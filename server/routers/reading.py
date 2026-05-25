"""
阅读历史路由 (S8-06)
============================
POST /api/reading/progress          — 保存阅读进度（需认证）
GET  /api/reading/progress?book=xxx — 获取某书阅读进度（需认证）
GET  /api/reading/last              — 获取最后阅读位置（需认证）
"""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse

from server.middleware.auth import get_current_user
from server.middleware.rate_limit import limiter
from server.services.chapter_db import (
    save_reading_progress,
    get_reading_progress,
    get_last_read,
)
from server.models.reading import ProgressRequest

router = APIRouter(prefix="/api/reading", tags=["reading"])


@router.post(
    "/progress",
    summary="保存阅读进度",
    responses={
        401: {"description": "未登录或 token 已过期"},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("30/minute")
async def save_progress(
    body: ProgressRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """保存当前章节的阅读进度。

    同一用户、同一书、同一回重复提交时自动更新（upsert）。
    progress 为 0~1 的小数，表示该回的阅读比例。
    """
    save_reading_progress(
        user_id=user['id'],
        book=body.book,
        chapter_no=body.chapter_no,
        progress=body.progress,
    )
    return JSONResponse({'ok': True})


@router.get(
    "/progress",
    summary="获取某书阅读进度",
    responses={
        401: {"description": "未登录或 token 已过期"},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("30/minute")
async def get_progress(
    request: Request,
    book: str = Query(..., description="书名，如：西游记"),
    user: dict = Depends(get_current_user),
):
    """获取当前用户在某本书的全部章节阅读进度列表。"""
    items = get_reading_progress(user_id=user['id'], book=book)
    return JSONResponse({'book': book, 'progress': items})


@router.get(
    "/last",
    summary="获取最后阅读位置",
    responses={
        401: {"description": "未登录或 token 已过期"},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("30/minute")
async def last_read(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """获取当前用户最后阅读的位置（哪本书、哪一回、进度多少）。

    用于"继续阅读"功能，返回按阅读时间倒序的最后一条记录。
    无阅读记录时返回 last_read: null。
    """
    item = get_last_read(user_id=user['id'])
    if not item:
        return JSONResponse({'last_read': None})
    return JSONResponse({'last_read': item})
