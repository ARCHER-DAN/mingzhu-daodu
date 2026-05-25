"""
API 限流中间件
基于 slowapi 实现，使用内存存储，按 IP 限流。

用法：
    from server.middleware.rate_limit import limiter

    @router.post("/login")
    @limiter.limit("10/minute")
    async def login(...):
        ...

在 main.py 中需设置 app.state.limiter = limiter 并注册异常处理器。
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Limiter 实例 — 模块级单例，router 和 main.py 共用
# ---------------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],           # 不设全局默认限制，由各端点单独控制
    storage_uri="memory://",
)


# ---------------------------------------------------------------------------
# 自定义 429 响应 — 友好中文提示
# ---------------------------------------------------------------------------
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """限流超限时返回 429 + 中文提示"""
    retry_after = int(getattr(exc, "retry_after", 60))
    return JSONResponse(
        status_code=429,
        content={
            "error": "请求过于频繁，请稍后再试",
            "retry_after_seconds": retry_after,
        },
    )
