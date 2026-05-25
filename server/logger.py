"""
日志模块封装

自动加载 server/logging.conf 配置文件，提供 get_logger() 函数。
日志文件输出到项目根目录的 logs/ 下，目录不存在时自动创建。
"""

import os
import logging
import logging.config
from pathlib import Path

# 项目根目录 = server/ 的父目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 日志输出目录
_LOG_DIR = _PROJECT_ROOT / "logs"

# 配置文件路径
_CONF_PATH = Path(__file__).resolve().parent / "logging.conf"

# 标记是否已初始化
_initialized = False


def _ensure_log_dir() -> None:
    """确保日志目录存在"""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def _init_logging() -> None:
    """初始化日志系统，只执行一次"""
    global _initialized
    if _initialized:
        return

    _ensure_log_dir()

    if _CONF_PATH.exists():
        logging.config.fileConfig(
            str(_CONF_PATH),
            defaults={"log_dir": str(_LOG_DIR)},
            disable_existing_loggers=False,
        )
    else:
        # 降级：没有配置文件时用基本配置
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.StreamHandler(),
                logging.handlers.RotatingFileHandler(
                    str(_LOG_DIR / "server.log"),
                    maxBytes=10 * 1024 * 1024,
                    backupCount=5,
                ),
            ],
        )

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """获取已配置的 logger

    Args:
        name: logger 名称，建议使用模块名（如 app.api、app.auth 等）

    Returns:
        配置好的 logging.Logger 实例
    """
    _init_logging()
    return logging.getLogger(name)
