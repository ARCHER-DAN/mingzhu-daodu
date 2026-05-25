"""
FastAPI 应用入口
名著导读 V3.0.0 — 后端工业化升级
"""
import sys
import os

# 确保项目根目录在 sys.path 中，以便复用 backend/ 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from server.middleware.logging import LoggingMiddleware
from server.middleware.exception import register_exception_handlers
from server.middleware.rate_limit import limiter, rate_limit_handler
from server.middleware.security import SecurityHeadersMiddleware

# ---------------------------------------------------------------------------
# 应用实例
# ---------------------------------------------------------------------------
app = FastAPI(
    title="名著导读 API",
    version="3.0.0",
    description="基于 Dify RAG 的 AI 名著导读平台 — 四大名著（西游记/三国演义/红楼梦/水浒传）智能问答与原文阅读",
    openapi_tags=[
        {"name": "auth", "description": "用户认证 — 注册、登录、获取当前用户信息"},
        {"name": "chapters", "description": "名著原文 — 章节目录查询与正文阅读"},
        {"name": "chat", "description": "AI 对话 — Dify RAG 智能问答（SSE 流式响应）"},
        {"name": "health", "description": "系统监控 — 服务健康检查与数据库连通性"},
        {"name": "reading", "description": "阅读历史 — 进度保存与继续阅读"},
        {"name": "admin", "description": "管理后台 — 用户列表、系统统计、详细健康检查"},
    ],
)

# ---------------------------------------------------------------------------
# 速率限制 — slowapi（挂载到 app.state，供路由装饰器使用）
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# ---------------------------------------------------------------------------
# 安全响应头中间件
# ---------------------------------------------------------------------------
app.add_middleware(SecurityHeadersMiddleware)

# ---------------------------------------------------------------------------
# CORS 中间件
# TODO: 生产环境收紧 allow_origins 白名单
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 日志中间件
# ---------------------------------------------------------------------------
app.add_middleware(LoggingMiddleware)

# ---------------------------------------------------------------------------
# 全局异常捕获
# ---------------------------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# 路由注册
# ---------------------------------------------------------------------------
from server.routers.health import router as health_router
app.include_router(health_router)

from server.routers import auth as auth_router
from server.routers import chapters as chapters_router
from server.routers import chat as chat_router
from server.routers import reading as reading_router
from server.routers import admin as admin_router

app.include_router(auth_router.router)
app.include_router(chapters_router.router)
app.include_router(chat_router.router)
app.include_router(reading_router.router)
app.include_router(admin_router.router)


# ---------------------------------------------------------------------------
# 静态文件挂载（前端 SPA）
# 必须在所有 API 路由注册之后挂载，确保 /api/* 路由优先匹配
# html=True 提供 SPA fallback：未匹配路由回退到 index.html
# ---------------------------------------------------------------------------
import os as _os
from fastapi.staticfiles import StaticFiles as _StaticFiles

_static_dir = _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "frontend", "dist"
)
if _os.path.isdir(_static_dir):
    app.mount(
        "/",
        _StaticFiles(directory=_static_dir, html=True),
        name="static",
    )


# ---------------------------------------------------------------------------
# 启动事件
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    """初始化数据库、业务表和管理员账号"""
    from backend.db import init_db
    from backend.init_admin import init_admin
    from server.services.chapter_db import init_chapters_table, init_reading_history_table

    init_db()                        # users 表
    init_admin()                     # 管理员账号
    init_chapters_table()            # chapters 表（S8-01）
    init_reading_history_table()     # reading_history 表（S8-05）

    print('[server] 名著导读 API v3.0.0 已启动 —— 数据库 + 业务表已初始化')


