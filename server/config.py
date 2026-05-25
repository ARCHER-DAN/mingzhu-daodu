"""从项目根目录 .env 文件加载配置"""
import os


def _load_dotenv():
    """简单 .env 解析器，不依赖 python-dotenv"""
    # server/config.py -> server/ -> 项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, '.env')
    if not os.path.exists(env_path):
        print(f'[config] .env 文件不存在: {env_path}')
        return
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, _, val = line.partition('=')
            key, val = key.strip(), val.strip()
            if key not in os.environ:
                os.environ[key] = val
    print(f'[config] .env 已加载: {env_path}')


_load_dotenv()


def env(key, default=''):
    val = os.environ.get(key, default)
    if not val and not default and key not in (
        'DIFY_EMAIL', 'DIFY_PASSWORD',  # 可选
        'ADMIN_DISPLAY_NAME',           # 有默认值
        'USER_EXPIRE_MINUTES',          # 有默认值
    ):
        raise RuntimeError(f'缺少环境变量: {key}，请配置 .env 文件')
    return val


# === 数据库配置 ===
MYSQL_HOST = env('MYSQL_HOST')
MYSQL_PORT = int(env('MYSQL_PORT', '3306'))
MYSQL_USER = env('MYSQL_USER')
MYSQL_PASSWORD = env('MYSQL_PASSWORD')
MYSQL_DATABASE = env('MYSQL_DATABASE')

# === JWT 配置 ===
JWT_SECRET = env('JWT_SECRET')
JWT_EXPIRE_HOURS = 72

# === 管理员配置 ===
ADMIN_EMAIL = env('ADMIN_EMAIL')
ADMIN_PASSWORD = env('ADMIN_PASSWORD')
ADMIN_DISPLAY_NAME = env('ADMIN_DISPLAY_NAME', '管理员')

# === Dify 配置 ===
DIFY_BASE_URL = env('DIFY_BASE_URL', 'http://your-dify-server:port')
DIFY_EMAIL = env('DIFY_EMAIL', '')
DIFY_PASSWORD = env('DIFY_PASSWORD', '')
DIFY_APP_API_KEY = env('DIFY_APP_API_KEY')

# === 用户过期配置 ===
USER_EXPIRE_MINUTES = int(env('USER_EXPIRE_MINUTES', '43200'))  # 默认 30 天

# === 服务器配置 ===
PORT = int(env('PORT', '8080'))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
