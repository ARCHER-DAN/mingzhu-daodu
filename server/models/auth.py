"""
认证相关 Pydantic 模型
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class RegisterRequest(BaseModel):
    """用户注册请求"""
    email: EmailStr = Field(
        ...,
        description="注册邮箱",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=6,
        description="登录密码，至少6位",
        examples=["mypassword123"],
    )
    display_name: Optional[str] = Field(
        default=None,
        description="显示名称，不传则取邮箱前缀",
        examples=["张三"],
    )


class LoginRequest(BaseModel):
    """用户登录请求"""
    email: EmailStr = Field(
        ...,
        description="登录邮箱",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        description="登录密码",
        examples=["mypassword123"],
    )


class UserResponse(BaseModel):
    """用户信息响应（不含 token）"""
    id: int = Field(..., description="用户 ID")
    email: str = Field(..., description="邮箱")
    display_name: str = Field(..., description="显示名称")
    is_admin: bool = Field(default=False, description="是否为管理员")
    own_api_key: Optional[str] = Field(default=None, description="用户自有 API Key")
    created_at: Optional[str] = Field(default=None, description="注册时间 ISO 格式")


class UserWithTokenResponse(BaseModel):
    """用户信息 + JWT token（注册/登录成功后返回）"""
    id: int = Field(..., description="用户 ID")
    email: str = Field(..., description="邮箱")
    display_name: str = Field(..., description="显示名称")
    is_admin: bool = Field(default=False, description="是否为管理员")
    own_api_key: Optional[str] = Field(default=None, description="用户自有 API Key")
    token: str = Field(..., description="JWT 认证令牌")


class ErrorResponse(BaseModel):
    """通用错误响应"""
    error: str = Field(..., description="错误描述")
