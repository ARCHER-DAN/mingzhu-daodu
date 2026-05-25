"""
JWT 认证依赖注入（FastAPI Depends）

用法：
    from server.middleware.auth import get_current_user

    @router.get("/me")
    async def me(user = Depends(get_current_user)):
        return user
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.auth import verify_token, get_user_by_id

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    从 Authorization: Bearer <token> 解析当前登录用户。

    返回 dict:
        user_id: int
        email: str
        display_name: str
        is_admin: bool
        own_api_key: str | None
        created_at: str | None

    Raises:
        HTTPException 401: 未登录或 token 无效/过期
        HTTPException 404: 用户不存在（已被删除）
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='未登录',
        )

    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='登录已过期',
        )

    user = get_user_by_id(payload['user_id'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='用户不存在',
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    可选认证：有 token 则解析用户，无 token 返回 None。
    用于对话代理等可选认证的场景。
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        return None

    user = get_user_by_id(payload['user_id'])
    return user


async def get_current_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    管理员权限依赖注入。

    必须先通过 get_current_user 认证，然后检查 is_admin 字段。
    非管理员返回 403。

    用法：
        @router.get("/admin/users")
        async def list_users(admin = Depends(get_current_admin)):
            ...

    Raises:
        HTTPException 401: 未登录（由 get_current_user 抛出）
        HTTPException 403: 已登录但不是管理员
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='需要管理员权限',
        )
    return current_user
