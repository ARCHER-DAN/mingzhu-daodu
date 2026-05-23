"""从 .env 文件加载配置"""
import os


def _load_dotenv():
    """简单 .env 解析器，不依赖 python-dotenv"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if not os.path.exists(env_path):
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


_load_dotenv()


def env(key, default=''):
    val = os.environ.get(key, default)
    if not val and not default:
        raise RuntimeError(f'缺少环境变量: {key}，请配置 .env 文件')
    return val
