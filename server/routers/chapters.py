"""
章节目录路由 (S8-03 + S8-04)
=============================================
GET /api/chapters?book=西游记               → 返回章节目录（DB 查询）
GET /api/chapters?book=西游记&chapter=1     → 返回章节正文（DB 查询）
GET /api/chapters/search?book=西游记&q=xxx  → 全文搜索（新增 S8-04）
GET /api/chapters/books                     → 所有可读书籍列表（新增 S8-03）

保持与旧版文件扫描 API 完全兼容的 JSON 格式。
"""
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from server.models.chapters import ChapterInfo, ChapterDetail, ChapterListResponse
from server.middleware.rate_limit import limiter
from server.services.chapter_db import (
    get_chapters_by_book,
    get_chapter,
    search_chapters,
    get_all_books,
)

router = APIRouter(prefix="/api", tags=["chapters"])


# ---------------------------------------------------------------------------
# GET /api/chapters/books  — 必须在 /api/chapters 前定义（FastAPI 精确路径优先）
# ---------------------------------------------------------------------------
@router.get(
    "/chapters/books",
    summary="获取所有可读书籍列表",
    responses={429: {"description": "请求过于频繁"}},
)
@limiter.limit("60/minute")
async def list_books(request: Request):
    """返回数据库中所有已导入的书籍名列表。

    Returns:
        { "books": ["三国演义", "水浒传", "红楼梦", "西游记"] }
    """
    books = get_all_books()
    return JSONResponse({'books': books})


# ---------------------------------------------------------------------------
# GET /api/chapters/search  — 全文搜索（新增 S8-04）
# ---------------------------------------------------------------------------
@router.get(
    "/chapters/search",
    summary="全文搜索章节内容",
    responses={
        400: {"description": "缺少搜索关键词"},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("30/minute")
async def search(
    request: Request,
    q: str = Query(..., description="搜索关键词（如：大闹天宫）"),
    book: str | None = Query(None, description="限定书名，不传则全局搜索"),
):
    """在章节标题和正文中进行全文搜索，按相关度降序排列。

    支持指定书名限定范围，或不指定书名进行跨书全局搜索。
    无结果时返回空数组，不返回 404。

    Returns:
        { "keyword": "大闹天宫", "book": "西游记", "results": [...] }
    """
    if not q or not q.strip():
        return JSONResponse({'error': '缺少搜索关键词'}, status_code=400)

    results = search_chapters(book=book, keyword=q.strip())
    return JSONResponse({
        'keyword': q.strip(),
        'book': book,
        'results': results,
    })


# ---------------------------------------------------------------------------
# GET /api/chapters  — 章节目录 / 章节正文
# ---------------------------------------------------------------------------
@router.get(
    "/chapters",
    summary="获取章节目录或章节正文",
    responses={
        400: {"description": "缺少 book 参数"},
        404: {"description": "书籍原文数据不存在或指定回号不存在"},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("60/minute")
async def list_chapters(
    request: Request,
    book: str = Query(..., description="书名，如：西游记/三国演义/红楼梦/水浒传"),
    chapter: int | None = Query(None, description="回号，不传则返回章节目录"),
):
    """获取指定名著的章节目录或具体章节正文。

    仅传 book 参数 → 返回该书的完整章节目录：
      { "book": "西游记", "chapters": [{"id": 1, "title": "...", "filename": "..."}, ...] }

    同时传 book + chapter → 返回指定回的正文：
      { "id": 1, "title": "...", "content": "..." }

    数据来源：MySQL chapters 表（S8-03 从文件扫描改为 DB 查询）。
    """
    if not book:
        return JSONResponse({'error': '缺少 book 参数'}, status_code=400)

    if chapter is not None:
        # --- 查询单章正文 ---
        ch = get_chapter(book, chapter)
        if not ch:
            return JSONResponse({'error': f'第{chapter}回不存在'}, status_code=404)
        return JSONResponse(ChapterDetail(**ch).model_dump())

    # --- 查询章节目录 ---
    chapters = get_chapters_by_book(book)
    if not chapters:
        return JSONResponse({'error': f'书籍 {book} 原文数据不存在'}, status_code=404)

    return JSONResponse(ChapterListResponse(
        book=book,
        chapters=[ChapterInfo(**c) for c in chapters],
    ).model_dump())
