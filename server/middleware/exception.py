"""
全局异常捕获中间件

捕获所有未被路由 handler 捕获的异常，统一返回 JSON 格式错误响应。
- HTTPException: 透传，404/405 返回友好提示
- ValidationError: 返回 422
- 其他异常: 500 + 日志记录

用法：
    from server.middleware.exception import register_exception_handlers
    register_exception_handlers(app)
"""

import os
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from server.logger import get_logger

logger = get_logger("app.api")


def _is_development() -> bool:
    """判断是否为开发模式"""
    return os.environ.get("APP_ENV", "production") == "development"


def _db_error_detail() -> str:
    """数据库错误的用户提示"""
    return "服务暂时不可用，请稍后再试"


def _is_db_error(exc: Exception) -> bool:
    """检测是否为数据库连接/操作异常"""
    try:
        import pymysql
        if isinstance(exc, pymysql.MySQLError):
            return True
    except ImportError:
        pass
    return False


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTPException: 404/405 友好提示，其余透传"""
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content={"error": "接口不存在"})
    if exc.status_code == 405:
        return JSONResponse(status_code=405, content={"error": "请求方法不允许"})

    # 其他 HTTPException（如 401/403 等）直接透传
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Pydantic ValidationError: 返回 422"""
    logger.warning("请求参数校验失败 [%s %s]: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": "请求参数校验失败",
            "detail": exc.errors() if _is_development() else "请求参数校验失败",
        },
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """FastAPI RequestValidationError: 返回 422 + 中文提示（覆盖 FastAPI 默认英文格式）"""
    errors = exc.errors()
    logger.warning("请求参数校验失败 [%s %s]: %s", request.method, request.url.path, errors)
    return JSONResponse(
        status_code=422,
        content={
            "error": "请求参数校验失败",
            "detail": errors,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """全局兜底: 捕获所有未处理异常，返回 500"""
    method = request.method
    path = request.url.path

    # 记录完整堆栈
    logger.error(
        "未处理异常 [%s %s]: %s\n%s",
        method,
        path,
        exc,
        traceback.format_exc(),
    )

    # 数据库错误：503 + 友好提示
    if _is_db_error(exc):
        return JSONResponse(
            status_code=503,
            content={"error": _db_error_detail()},
        )

    # 通用 500
    detail = str(exc) if _is_development() else "服务器内部错误"
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误", "detail": detail},
    )


def register_exception_handlers(app):
    """在 FastAPI app 上注册所有全局异常处理器"""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info("全局异常处理器已注册")
