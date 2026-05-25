"""
FastAPI 生产启动脚本
使用 uvicorn 编程方式启动，适配 Windows 环境

用法：
    python scripts/start_fastapi.py

等同：
    uvicorn server.main:app --host 0.0.0.0 --port 8080 --workers 1
"""

import logging
import os
import sys

# 确保项目根目录在 Python 路径中
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)


def _ensure_log_dir():
    """确保日志目录存在"""
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "logs",
    )
    os.makedirs(log_dir, exist_ok=True)


def main():
    _ensure_log_dir()

    # 基础日志配置（server/logger.py 加载时可能因 logging.conf 问题失败，
    # 这里先设一个兜底，确保启动日志不丢失）
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # 尝试通过 server.logger 加载正式日志配置
    try:
        from server.logger import get_logger
        logger = get_logger("server")
    except Exception:
        # TODO: server/logging.conf 中 handler_file 的 class 写的是
        #       `handlers.RotatingFileHandler`，应为 `logging.handlers.RotatingFileHandler`，
        #       导致 logging.config.fileConfig 解析失败。当前用 basicConfig 兜底，待后端修复后可移除此 try/except。
        logging.getLogger("server").warning(
            "server.logger 初始化失败（可能因 logging.conf 配置问题），使用默认日志配置"
        )
        logger = logging.getLogger("server")

    try:
        import uvicorn
    except ImportError:
        logger.critical("uvicorn 未安装，请运行: pip install uvicorn[standard]")
        sys.exit(1)

    logger.info("正在启动名著导读 FastAPI 服务 (V3.0.0)...")

    try:
        uvicorn.run(
            "server.main:app",
            host="0.0.0.0",
            port=8080,
            workers=1,               # Windows 上 multiprocessing 不稳定，单 worker
            access_log=False,        # 使用 LoggingMiddleware + logging.conf 体系
            reload=False,            # 生产模式，禁用热重载
        )
    except KeyboardInterrupt:
        logger.info("服务已手动停止")
    except Exception as e:
        logger.critical(f"服务启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
