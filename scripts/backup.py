#!/usr/bin/env python3
"""名著导读 自动化备份脚本
S7-07: 备份数据库 + data/ + 服务配置，保留最近7天

功能：
  1. 读取 .env 获取数据库连接信息
  2. 备份数据库 (mysqldump / PyMySQL 降级)
  3. 打包 data/ 目录 (tar.gz / zip)
  4. 复制 server/logging.conf + .env 到备份目录
  5. 清理超过 7 天的旧备份
  6. 日志写入 logs/backup.log + 控制台输出

用法:
  python scripts/backup.py
"""

import os
import sys
import re
import shutil
import subprocess
import logging
from datetime import datetime, timedelta

# ----- 路径常量 -----
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(ROOT, 'backups')
LOG_DIR = os.path.join(ROOT, 'logs')


# ============================================================
#  配置加载
# ============================================================

def load_env():
    """从项目根 .env 解析配置（不依赖 python-dotenv）"""
    env_path = os.path.join(ROOT, '.env')
    if not os.path.exists(env_path):
        raise FileNotFoundError(f'.env 文件不存在: {env_path}')

    env = {}
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, _, val = line.partition('=')
            env[key.strip()] = val.strip()
    return env


# ============================================================
#  日志
# ============================================================

def setup_logging():
    """初始化双通道日志（控制台 + 文件）"""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, 'backup.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger('backup')


# ============================================================
#  数据库备份
# ============================================================

def _mysqldump_available():
    """检查 mysqldump 是否可用"""
    try:
        subprocess.run(
            ['mysqldump', '--version'],
            capture_output=True, text=True, timeout=10,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def backup_db_mysqldump(env, timestamp):
    """使用 mysqldump 导出全库"""
    output = os.path.join(BACKUP_DIR, f'db_backup_{timestamp}.sql')
    cmd = [
        'mysqldump',
        f'--host={env["MYSQL_HOST"]}',
        f'--port={env["MYSQL_PORT"]}',
        f'--user={env["MYSQL_USER"]}',
        f'--password={env["MYSQL_PASSWORD"]}',
        '--single-transaction',
        '--routines',
        '--triggers',
        '--add-drop-table',
        env['MYSQL_DATABASE'],
    ]

    safe_cmd = ' '.join(cmd[:4]) + ' --password=*** ' + ' '.join(cmd[5:])
    logging.info('运行 mysqldump: %s', safe_cmd)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            logging.error('mysqldump 返回非零: %s', proc.stderr.strip())
            return None
        with open(output, 'w', encoding='utf-8') as f:
            f.write(proc.stdout)
        sz = os.path.getsize(output) / 1024
        logging.info('数据库备份完成: %s (%.1f KB)', output, sz)
        return output
    except subprocess.TimeoutExpired:
        logging.error('mysqldump 超时 (120s)')
        return None
    except OSError as e:
        logging.error('mysqldump 执行失败: %s', e)
        return None


def backup_db_pymysql(env, timestamp):
    """PyMySQL 降级方案：仅导出 users 表为 INSERT 语句"""
    try:
        import pymysql
    except ImportError:
        logging.error('pymysql 未安装，请先执行: pip install pymysql')
        return None

    output = os.path.join(BACKUP_DIR, f'db_backup_{timestamp}.sql')
    logging.info('mysqldump 不可用，降级为 PyMySQL 导出 users 表')

    try:
        conn = pymysql.connect(
            host=env['MYSQL_HOST'],
            port=int(env['MYSQL_PORT']),
            user=env['MYSQL_USER'],
            password=env['MYSQL_PASSWORD'],
            database=env['MYSQL_DATABASE'],
            charset='utf8mb4',
        )
    except pymysql.Error as e:
        logging.error('数据库连接失败: %s', e)
        return None

    try:
        with conn.cursor() as cur:
            # CREATE TABLE
            cur.execute('SHOW CREATE TABLE users')
            create_stmt = cur.fetchone()[1]

            # 全量数据
            cur.execute('SELECT * FROM users')
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        with open(output, 'w', encoding='utf-8') as f:
            f.write(
                '-- 名著导读 users 表备份\n'
                f'-- 数据库: {env["MYSQL_DATABASE"]}\n'
                f'-- 导出时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n'
            )
            f.write(f'DROP TABLE IF EXISTS `users`;\n')
            f.write(f'{create_stmt};\n\n')

            for row in rows:
                vals = []
                for v in row:
                    if v is None:
                        vals.append('NULL')
                    elif isinstance(v, (int, float)):
                        vals.append(str(v))
                    elif isinstance(v, bytes):
                        vals.append(f"'{v.decode('utf-8', errors='replace')}'")
                    else:
                        safe = str(v).replace('\\', '\\\\').replace("'", "''")
                        vals.append(f"'{safe}'")
                f.write(
                    f'INSERT INTO `users` '
                    f'(`{"`, `".join(columns)}`) '
                    f'VALUES ({", ".join(vals)});\n'
                )

        conn.close()
        sz = os.path.getsize(output) / 1024
        logging.info('数据库备份完成 (PyMySQL): %s (%.1f KB)', output, sz)
        return output

    except pymysql.Error as e:
        logging.error('PyMySQL 导出失败: %s', e)
        try:
            conn.close()
        except Exception:
            pass
        return None


# ============================================================
#  数据文件备份
# ============================================================

def _tar_available():
    """检查 tar 是否可用"""
    try:
        subprocess.run(
            ['tar', '--version'],
            capture_output=True, text=True, timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def backup_data(timestamp):
    """打包 data/ 目录（优先 tar.gz，降级 zip）"""
    data_dir = os.path.join(ROOT, 'data')
    if not os.path.isdir(data_dir):
        logging.warning('data/ 目录不存在，跳过数据备份')
        return None

    if _tar_available():
        output = os.path.join(BACKUP_DIR, f'data_backup_{timestamp}.tar.gz')
        try:
            subprocess.run(
                ['tar', '-czf', output, '-C', ROOT, 'data'],
                check=True, timeout=300,
            )
            sz = os.path.getsize(output) / 1024 / 1024
            logging.info('数据备份完成 (tar): %s (%.1f MB)', output, sz)
            return output
        except subprocess.TimeoutExpired:
            logging.error('tar 打包超时 (300s)，切换到 zip')
        except subprocess.CalledProcessError as e:
            logging.error('tar 打包失败: %s，切换到 zip', e)

    # ZIP 降级
    output = os.path.join(BACKUP_DIR, f'data_backup_{timestamp}.zip')
    base = os.path.join(BACKUP_DIR, f'data_backup_{timestamp}')
    try:
        shutil.make_archive(base, 'zip', ROOT, 'data')
        sz = os.path.getsize(output) / 1024 / 1024
        logging.info('数据备份完成 (zip): %s (%.1f MB)', output, sz)
        return output
    except OSError as e:
        logging.error('zip 打包失败: %s', e)
        return None


# ============================================================
#  配置文件备份
# ============================================================

def backup_config(timestamp):
    """复制 server/logging.conf + .env 到备份目录"""
    sources = [
        os.path.join('server', 'logging.conf'),
        '.env',
    ]

    dest_dir = os.path.join(BACKUP_DIR, f'config_backup_{timestamp}')
    copied = []

    for rel in sources:
        src = os.path.join(ROOT, rel)
        if os.path.isfile(src):
            dst = os.path.join(dest_dir, os.path.basename(rel))
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(rel)
        else:
            logging.warning('配置文件缺失: %s', rel)

    if copied:
        logging.info('配置备份完成: %s (%s)', dest_dir, ', '.join(copied))
        return dest_dir

    if os.path.isdir(dest_dir):
        shutil.rmtree(dest_dir, ignore_errors=True)
    logging.warning('没有可备份的配置文件')
    return None


# ============================================================
#  清理策略
# ============================================================

_DATE_PATTERN = re.compile(r'(\d{8})_\d{6}')


def cleanup_old_backups(retention_days=7):
    """删除超过 retention_days 天的备份文件"""
    now = datetime.now()
    cutoff = now - timedelta(days=retention_days)

    cleaned = 0
    for entry in os.listdir(BACKUP_DIR):
        if entry == '.gitkeep':
            continue

        m = _DATE_PATTERN.search(entry)
        if not m:
            continue

        try:
            file_date = datetime.strptime(m.group(1), '%Y%m%d')
        except ValueError:
            continue

        if file_date >= cutoff:
            continue

        full = os.path.join(BACKUP_DIR, entry)
        try:
            if os.path.isdir(full):
                shutil.rmtree(full)
            else:
                os.remove(full)
            logging.info('清理旧备份: %s', entry)
            cleaned += 1
        except OSError as e:
            logging.error('无法删除 %s: %s', entry, e)

    if cleaned:
        logging.info('已清理 %d 个旧备份', cleaned)
    else:
        logging.info('没有需要清理的旧备份')


# ============================================================
#  主流程
# ============================================================

def main():
    logger = setup_logging()
    logger.info('=' * 60)
    logger.info('名著导读每日备份 - 开始')

    os.makedirs(BACKUP_DIR, exist_ok=True)

    # 1. 加载配置
    try:
        env = load_env()
        logger.info(
            '已加载 .env → %s@%s:%s',
            env['MYSQL_DATABASE'], env['MYSQL_HOST'], env['MYSQL_PORT'],
        )
    except Exception as e:
        logger.error('配置加载失败: %s', e)
        sys.exit(1)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    results = {}

    # 2. 数据库备份
    try:
        if _mysqldump_available():
            results['db'] = backup_db_mysqldump(env, ts)
        else:
            logger.warning('mysqldump 不可用，降级为 PyMySQL')
            results['db'] = backup_db_pymysql(env, ts)
    except Exception as e:
        logger.error('数据库备份异常: %s', e)
        results['db'] = None

    # 3. 数据文件备份
    try:
        results['data'] = backup_data(ts)
    except Exception as e:
        logger.error('数据备份异常: %s', e)
        results['data'] = None

    # 4. 配置备份
    try:
        results['config'] = backup_config(ts)
    except Exception as e:
        logger.error('配置备份异常: %s', e)
        results['config'] = None

    # 5. 清理
    try:
        cleanup_old_backups()
    except Exception as e:
        logger.error('清理旧备份异常: %s', e)

    # 6. 汇总
    logger.info('--- 备份结果 ---')
    for k, v in results.items():
        status = 'OK' if v else 'FAIL'
        logger.info('  %s: %s -> %s', k, status, v or '(none)')
    logger.info('=' * 60)


if __name__ == '__main__':
    main()
