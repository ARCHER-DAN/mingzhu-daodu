"""
认证路由 — 注册 / 登录 / 获取当前用户
POST /api/auth/register  — 5次/分钟/IP（限流）
POST /api/auth/login     — 10次/分钟/IP（限流）+ 5次失败锁定15分钟
GET  /api/auth/me        — 30次/分钟/IP（限流）
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from backend.auth import register_user, login_user, create_token
from server.models.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    UserWithTokenResponse,
    ErrorResponse,
)
from server.middleware.auth import get_current_user
from server.middleware.rate_limit import limiter
from server.services.login_guard import (
    check_login_allowed,
    record_login_failure,
    record_login_success,
    get_lock_remaining_seconds,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserWithTokenResponse,
    status_code=201,
    summary="用户注册",
    responses={
        409: {"description": "该邮箱已注册", "model": ErrorResponse},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("5/minute")
async def auth_register(body: RegisterRequest, request: Request):
    """注册新用户账号。

    提交邮箱、密码和可选的显示名称，成功后返回用户信息及 JWT 认证令牌。
    新注册用户默认有 30 天有效期，到期后自动清理。
    """
    email = body.email.strip()
    password = body.password
    display_name = body.display_name.strip() if body.display_name else None

    user = register_user(email, password, display_name or None)
    if user is None:
        return JSONResponse({'error': '该邮箱已注册'}, status_code=409)

    user['token'] = create_token(user)
    return JSONResponse(user, status_code=201)


@router.post(
    "/login",
    response_model=UserWithTokenResponse,
    summary="用户登录",
    responses={
        401: {"description": "邮箱或密码错误", "model": ErrorResponse},
        429: {"description": "请求过于频繁或登录失败次数过多"},
    },
)
@limiter.limit("10/minute")
async def auth_login(body: LoginRequest, request: Request):
    """用户登录，验证邮箱密码后返回用户信息及 JWT 认证令牌。

    JWT 令牌有效期 72 小时，过期后需重新登录。
    连续 5 次登录失败后，同 IP 锁定 15 分钟。
    """
    email = body.email.strip()
    password = body.password

    # --- 登录失败锁定检查（IP 级别） ---
    client_ip = request.client.host if request.client else "unknown"

    if not check_login_allowed(client_ip):
        remaining = get_lock_remaining_seconds(client_ip)
        minutes = remaining // 60
        seconds = remaining % 60
        msg = f"登录尝试过于频繁，请{minutes}分{seconds}秒后再试"
        return JSONResponse({"error": msg}, status_code=429)

    # --- 尝试验证 ---
    user = login_user(email, password)
    if user is None:
        record_login_failure(client_ip)
        return JSONResponse({'error': '邮箱或密码错误'}, status_code=401)

    # --- 登录成功，清除失败记录 ---
    record_login_success(client_ip)
    user['token'] = create_token(user)
    return JSONResponse(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    responses={
        401: {"description": "未登录或 token 已过期"},
        404: {"description": "用户不存在"},
        429: {"description": "请求过于频繁"},
    },
)
@limiter.limit("30/minute")
async def auth_me(user: dict = Depends(get_current_user), request: Request = None):
    """获取当前登录用户信息。

    需要在请求头中携带 Bearer token。token 过期或无效将返回 401。
    """
    return JSONResponse(user)
