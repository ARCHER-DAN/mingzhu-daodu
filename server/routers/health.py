"""
健康检查端点
GET /api/health — 返回服务状态、时间戳、版本号、数据库连通性
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Request

from server.middleware.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["health"])


@router.get(
    "/health",
    summary="健康检查",
    responses={
        200: {
            "description": (
                "返回服务健康状态。`status` 为 'ok'（数据库连通）或 'degraded'（数据库断开）；"
                "`database` 为 'connected' 或 'disconnected'；"
                "`version` 为当前 API 版本号；`timestamp` 为 ISO 8601 UTC 时间。"
            ),
        },
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("60/minute")
def health_check(request: Request = None):
    """
    健康检查接口。

    返回字段：
      - status (str): 'ok' 或 'degraded'
      - timestamp (str): 当前 UTC 时间 ISO 8601 格式
      - version (str): API 版本号
      - database (str): 'connected' 或 'disconnected'
    """
    db_status = "disconnected"
    try:
        from backend.db import get_conn
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    overall = "ok" if db_status == "connected" else "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "3.0.0",
        "database": db_status,
    }
