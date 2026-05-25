"""
阅读历史相关 Pydantic 模型
"""
from pydantic import BaseModel, Field
from typing import Optional


class ProgressRequest(BaseModel):
    """保存阅读进度请求（S8-06）"""
    book: str = Field(..., description="书名", examples=["西游记"])
    chapter_no: int = Field(..., description="回号", examples=[1])
    progress: float = Field(
        default=0,
        ge=0,
        le=1,
        description="阅读进度，0~1 之间的小数（如 0.5 表示阅读了一半）",
        examples=[0.5],
    )


class ProgressItem(BaseModel):
    """单条阅读进度"""
    book: str = Field(..., description="书名")
    chapter_no: int = Field(..., description="回号")
    progress: float = Field(..., description="阅读进度 0~1")
    updated_at: Optional[str] = Field(default=None, description="最后更新时间 ISO 格式")


class LastReadInfo(BaseModel):
    """最后阅读位置"""
    book: str = Field(..., description="书名")
    chapter_no: int = Field(..., description="回号")
    progress: float = Field(..., description="阅读进度 0~1")
    updated_at: Optional[str] = Field(default=None, description="最后更新时间 ISO 格式")
