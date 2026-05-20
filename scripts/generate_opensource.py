"""生成开源副本——复制文件并替换敏感信息为环境变量占位符"""
import os, shutil, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = 'v2.0.5'
DST = os.path.join(ROOT, 'opensource', f'Introduction_Classics_{VERSION}')

# 敏感信息替换规则
REPLACE_RULES = [
    # 密码类
    (r"os.environ.get('DIFY_PASSWORD', '')", "os.environ.get('DIFY_PASSWORD', '')"),
    (r'os.environ.get('DIFY_PASSWORD', '')', "os.environ.get('DIFY_PASSWORD', '')"),
    (r"os.environ.get('MYSQL_PASSWORD', '')", "os.environ.get('MYSQL_PASSWORD', '')"),
    (r"os.environ.get('ADMIN_PASSWORD', '')", "os.environ.get('ADMIN_PASSWORD', '')"),
    (r"os.environ.get('JWT_SECRET', 'change-me')", "os.environ.get('JWT_SECRET', 'change-me')"),
    # 邮箱
    (r"os.environ.get('DIFY_EMAIL', '')", "os.environ.get('DIFY_EMAIL', '')"),
    (r'os.environ.get('DIFY_EMAIL', '')', "os.environ.get('DIFY_EMAIL', '')"),
    # API Key
    (r"apiKey: (await fetch('/api/config').then(r=>r.json()))['西游记'].apiKey",
     "apiKey: (await fetch('/api/config').then(r=>r.json()))['西游记'].apiKey"),
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
COPY_DIRS = ['backend', 'scripts', 'frontend', 'data', 'docs', 'android']

# 排除的目录/文件
EXCLUDE = [
    '__pycache__', '.venv', 'node_modules', 'dist', '.gradle', 'build',
    '.claude', '.env', 'opensource', '.git',
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
        shutil.rmtree(DST)
    os.makedirs(DST)

    # 复制根目录文件
    for f in ['requirements.txt', '.gitignore']:
        src = os.path.join(ROOT, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(DST, f))

    # 复制子目录
    for d in COPY_DIRS:
        src = os.path.join(ROOT, d)
        if os.path.exists(src):
            copy_tree(src, os.path.join(DST, d))

    # 清理 App.jsx 特殊处理
    app_js = os.path.join(DST, 'frontend', 'src', 'App.jsx')
    if os.path.exists(app_js):
        with open(app_js, encoding='utf-8') as f:
            content = f.read()
        # 确保 API key 从服务端获取
        content = content.replace(
            "apiKey: (await fetch('/api/config').then(r=>r.json()))['西游记'].apiKey",
            "''  // 从服务端 /api/config 获取"
        )
        with open(app_js, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f'开源副本已生成: {DST}')


if __name__ == '__main__':
    main()
