"""生成开源副本——复制文件并替换敏感信息为环境变量占位符"""
import os, shutil, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = 'v2.1.0'
DST = os.path.join(ROOT, 'opensource', f'Introduction_Classics_{VERSION}')

# 敏感信息替换规则
REPLACE_RULES = [
    # 密码类
    (r"os.environ.get('DIFY_PASSWORD', '')", "os.environ.get('DIFY_PASSWORD', '')"),
    (r'os.environ.get('DIFY_PASSWORD', '')', "os.environ.get('DIFY_PASSWORD', '')"),
    (ros.environ.get('DIFY_PASSWORD', ''), 'DIFY_PASSWORD_PLACEHOLDER'),
    (r"os.environ.get('MYSQL_PASSWORD', '')", "os.environ.get('MYSQL_PASSWORD', '')"),
    (ros.environ.get('MYSQL_PASSWORD', ''), 'MYSQL_PASSWORD_PLACEHOLDER'),
    (r"os.environ.get('ADMIN_PASSWORD', '')", "os.environ.get('ADMIN_PASSWORD', '')"),
    (ros.environ.get('ADMIN_PASSWORD', ''), 'ADMIN_PASSWORD_PLACEHOLDER'),
    (r"os.environ.get('JWT_SECRET', 'change-me')", "os.environ.get('JWT_SECRET', 'change-me')"),
    (ros.environ.get('JWT_SECRET', 'change-me'), 'JWT_SECRET_PLACEHOLDER'),
    # 邮箱
    (r"os.environ.get('DIFY_EMAIL', '')", "os.environ.get('DIFY_EMAIL', '')"),
    (r'os.environ.get('DIFY_EMAIL', '')', "os.environ.get('DIFY_EMAIL', '')"),
    (r"os.environ.get('ADMIN_EMAIL', 'admin@example.com')", "os.environ.get('ADMIN_EMAIL', 'admin@example.com')"),
    (r'os.environ.get('ADMIN_EMAIL', 'admin@example.com')', "os.environ.get('ADMIN_EMAIL', 'admin@example.com')"),
    (r'admin@classics\.cn', 'admin@example.com'),
    # API Key
    (r"apiKey: (await fetch('/api/config').then(r=>r.json()))['西游记'].apiKey",
     "apiKey: (await fetch('/api/config').then(r=>r.json()))['西游记'].apiKey"),
    (r'DIFY_APP_API_KEY_PLACEHOLDER', 'DIFY_APP_API_KEY_PLACEHOLDER'),
    # 内网IP
    (r'192\.168\.31\.117:8083', 'your-dify-server:port'),
    (r'192\.168\.31\.215:8080', 'your-frontend-server:8080'),
    (r'192\.168\.134\.133:8088', 'your-dify-server:port'),
    (r'192\.168\.31\.117:38787', 'your-mysql-server:38787'),
    (r'192\.168\.31\.117', 'your-server'),
    (r'192\.168\.31\.215', 'your-frontend-server'),
    (r'192\.168\.134\.133', 'your-server'),
    # cpolar 域名
    (r'http://[a-z0-9]+\.r18\.vip\.cpolar\.cn', 'http://your-domain.cpolar.cn'),
    (r'https://[a-z0-9]+\.r18\.vip\.cpolar\.cn', 'https://your-domain.cpolar.cn'),
    # 团队成员姓名 → 匿名
    ('PM', 'PM'),
    ('前端', '前端'),
    ('后端', '后端'),
    ('运维', '运维'),
    ('测试', '测试'),
    ('脚本', '脚本'),
    ('权限', '权限'),
    ('备份', '备份'),
    ('外网', '外网'),
    ('安卓', '安卓'),
    ('文档', '文档'),
    ('隐私', '隐私'),
    ('开源', '开源'),
]

# 需要复制的目录
COPY_DIRS = ['backend', 'scripts', 'frontend', 'data', 'docs']

# 排除的目录/文件
EXCLUDE = [
    '__pycache__', '.venv', 'node_modules', 'dist', '.gradle', 'build',
    '.claude', '.env', '.launcher_creds.json', 'opensource', '.git',
    'test-results', 'backups',
    # docs: 只保留开发文档
    'Dify平台技术文档.md', '测试报告_S1T08_检索效果.md',
    '测试数据_S1T08_检索效果.json', '需求文档.md', '测试报告_Sprint5.md',
]


def should_exclude(path):
    for ex in EXCLUDE:
        if ex in path.replace('\\', '/').split('/'):
            return True
    return False


def clean_file(filepath):
    """替换文件内容中的敏感信息"""
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError):
        return  # 跳过二进制/无权限文件

    original = content
    for pattern, replacement in REPLACE_RULES:
        content = re.sub(pattern, replacement, content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)


def copy_tree(src, dst):
    """复制目录树并清洗"""
    if should_exclude(src):
        return
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if should_exclude(s):
            continue
        if os.path.isdir(s):
            copy_tree(s, d)
        else:
            shutil.copy2(s, d)
            clean_file(d)


def main():
    if os.path.exists(DST):
        try:
            shutil.rmtree(DST)
        except PermissionError:
            import tempfile, time
            tmp = DST + '_tmp_' + str(int(time.time()))
            shutil.move(DST, tmp)
            shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(DST, exist_ok=True)

    # 复制根目录文件并清洗
    for f in ['requirements.txt', '.env.example']:
        src = os.path.join(ROOT, f)
        if os.path.exists(src):
            dst = os.path.join(DST, f)
            shutil.copy2(src, dst)
            clean_file(dst)

    # 复制子目录
    for d in COPY_DIRS:
        src = os.path.join(ROOT, d)
        if os.path.exists(src):
            copy_tree(src, os.path.join(DST, d))

    print(f'开源副本已生成: {DST}')


if __name__ == '__main__':
    main()
