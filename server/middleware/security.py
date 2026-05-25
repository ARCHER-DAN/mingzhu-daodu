"""
安全响应头中间件
为所有 HTTP 响应添加安全相关的响应头。

- X-Content-Type-Options: 禁止 MIME 类型嗅探
- X-Frame-Options: 禁止页面被嵌入 iframe（防点击劫持）
- X-XSS-Protection: 启用浏览器 XSS 过滤器
- Strict-Transport-Security: HSTS（生产环境启用，需 HTTPS）

用法：
    from server.middleware.security import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有 HTTP 响应添加安全头"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # 禁止浏览器 MIME 类型嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 禁止页面被嵌入 iframe（防点击劫持）
        response.headers["X-Frame-Options"] = "DENY"

        # 启用浏览器 XSS 过滤器
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HSTS（仅 HTTPS 环境启用，默认注释）
        # 生产环境部署 HTTPS 后取消注释：
        # response.headers["Strict-Transport-Security"] = (
        #     "max-age=31536000; includeSubDomains"
        # )

        return response
