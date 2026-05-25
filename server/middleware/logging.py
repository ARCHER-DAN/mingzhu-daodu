"""
请求/响应日志中间件

记录每个 HTTP 请求的 method、path、query_string、client_ip、
响应 status_code 和处理耗时（毫秒）。

使用方式：
    from server.middleware.logging import LoggingMiddleware
    from fastapi import FastAPI

    app = FastAPI()
    app.add_middleware(LoggingMiddleware)
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from server.logger import get_logger

logger = get_logger("app.api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求/响应日志中间件

    记录格式: GET /api/chapters?book=西游记 200 12ms
    异常请求（5xx）同样记录。
    """

    async def dispatch(self, request: Request, call_next):
        # 获取请求信息
        method = request.method
        path = request.url.path
        query_string = request.url.query
        client_ip = _get_client_ip(request)

        # 构建请求描述
        full_path = path
        if query_string:
            full_path = f"{path}?{query_string}"

        start_time = time.monotonic()

        try:
            response: Response = await call_next(request)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            status_code = response.status_code

            logger.info(
                "%s %s %s %dms [%s]",
                method,
                full_path,
                status_code,
                elapsed_ms,
                client_ip,
            )
            return response

        except Exception:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.exception(
                "%s %s 500 %dms [%s] (unhandled)",
                method,
                full_path,
                elapsed_ms,
                client_ip,
            )
            raise


def _get_client_ip(request: Request) -> str:
    """从请求中提取客户端真实 IP

    优先从 X-Forwarded-For 头获取（用于反向代理场景），
    否则取 request.client.host。
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
