"""
管理员 API (S9-04)
===================
GET /api/admin/users  — 用户列表，分页，需管理员权限
GET /api/admin/stats  — 系统统计，需管理员权限
GET /api/admin/health — 详细健康检查，无需认证
"""
import math
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse

from server.middleware.auth import get_current_user, get_current_admin
from server.middleware.rate_limit import limiter
from server.config import DIFY_BASE_URL

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# 数据库查询辅助
# ---------------------------------------------------------------------------

def _db_fetch(sql: str, params=None) -> list:
    """执行查询并返回全部结果行（tuple list）"""
    from backend.db import get_conn
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def _db_execute(sql: str, params=None) -> int:
    """执行非查询 SQL，返回受影响行数"""
    from backend.db import get_conn
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/admin/users
# ---------------------------------------------------------------------------

@router.get(
    "/users",
    summary="获取用户列表",
    responses={
        200: {"description": "用户列表及分页信息"},
        401: {"description": "未登录或 token 已过期"},
        403: {"description": "非管理员，权限不足"},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("30/minute")
async def list_users(
    request: Request,
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，最大 100"),
    admin: dict = Depends(get_current_admin),
):
    """获取所有注册用户列表（管理员专属）。

    按 id 降序排列，最新注册的用户排在最前面。
    返回字段包含 id、email、display_name、is_admin、created_at、expire_at。
    """
    offset = (page - 1) * page_size

    total = _db_fetch('SELECT COUNT(*) FROM users')[0][0]
    total_pages = max(1, math.ceil(total / page_size))

    rows = _db_fetch(
        'SELECT id, email, display_name, is_admin, created_at, expire_at '
        'FROM users ORDER BY id DESC LIMIT %s OFFSET %s',
        (page_size, offset),
    )

    users = []
    for r in rows:
        users.append({
            'id': r[0],
            'email': r[1],
            'display_name': r[2],
            'is_admin': bool(r[3]),
            'created_at': r[4].isoformat() if r[4] else None,
            'expire_at': r[5].isoformat() if r[5] else None,
        })

    return JSONResponse({
        'users': users,
        'total': total,
        'total_pages': total_pages,
        'page': page,
        'page_size': page_size,
    })


# ---------------------------------------------------------------------------
# GET /api/admin/stats
# ---------------------------------------------------------------------------

@router.get(
    "/stats",
    summary="获取系统统计",
    responses={
        200: {"description": "系统统计数据"},
        401: {"description": "未登录或 token 已过期"},
        403: {"description": "非管理员，权限不足"},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("30/minute")
async def get_stats(
    request: Request,
    admin: dict = Depends(get_current_admin),
):
    """获取系统全局统计数据。

    包含：
      - total_users: 总注册用户数
      - today_active_users: 今日有阅读记录的用户数
      - total_reading_records: 阅读历史总记录数
      - database_status: 数据库连接状态
      - dify_status: Dify 服务可达性
    """
    # 总用户数
    total_users = _db_fetch('SELECT COUNT(*) FROM users')[0][0]

    # 今日活跃用户数
    today_active = _db_fetch(
        'SELECT COUNT(DISTINCT user_id) FROM reading_history '
        'WHERE DATE(updated_at) = CURDATE()'
    )[0][0]

    # 阅读记录总数（表可能尚未初始化）
    total_reading = 0
    try:
        total_reading = _db_fetch('SELECT COUNT(*) FROM reading_history')[0][0]
    except Exception:
        pass

    # 数据库连接状态
    db_status = "disconnected"
    try:
        from backend.db import get_conn
        conn_test = get_conn()
        with conn_test.cursor() as cur:
            cur.execute('SELECT 1')
        conn_test.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Dify 可达性
    dify_status = "disconnected"
    try:
        urllib.request.urlopen(DIFY_BASE_URL, timeout=5)
        dify_status = "connected"
    except Exception:
        dify_status = "disconnected"

    return JSONResponse({
        'total_users': total_users,
        'today_active_users': today_active,
        'total_reading_records': total_reading,
        'database_status': db_status,
        'dify_status': dify_status,
    })


# ---------------------------------------------------------------------------
# GET /api/admin/health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    summary="详细健康检查",
    responses={
        200: {"description": "服务、数据库、Dify 三者状态"},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("60/minute")
async def admin_health(request: Request):
    """无需认证的健康检查端点，用于管理后台监控面板。

    返回服务（始终 ok）、数据库、Dify 三者的连通状态。
    比 /api/health 多了 dify 可达性检测。
    """
    from datetime import datetime, timezone

    # 数据库连通性
    db_status = "disconnected"
    try:
        from backend.db import get_conn
        conn_test = get_conn()
        with conn_test.cursor() as cur:
            cur.execute('SELECT 1')
        conn_test.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Dify 可达性
    dify_status = "disconnected"
    try:
        urllib.request.urlopen(DIFY_BASE_URL, timeout=5)
        dify_status = "connected"
    except Exception:
        dify_status = "disconnected"

    overall = "ok" if (db_status == "connected" and dify_status == "connected") else "degraded"

    return JSONResponse({
        'status': overall,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '3.0.0',
        'database': db_status,
        'dify': dify_status,
    })
