"""
章节相关 Pydantic 模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class ChapterInfo(BaseModel):
    """章节目录条目"""
    id: int = Field(..., description="回号", examples=[1])
    title: str = Field(..., description="回目标题", examples=["灵根育孕源流出 心性修持大道生"])
    filename: str = Field(..., description="文件名", examples=["第001回_灵根育孕源流出 心性修持大道生.txt"])


class ChapterDetail(BaseModel):
    """章节详情（含正文）"""
    id: int = Field(..., description="回号", examples=[1])
    title: str = Field(..., description="回目标题", examples=["灵根育孕源流出 心性修持大道生"])
    content: str = Field(..., description="章节正文全文")


class ChapterListResponse(BaseModel):
    """章节目录响应"""
    book: str = Field(..., description="书名", examples=["西游记"])
    chapters: list[ChapterInfo] = Field(default_factory=list, description="章节列表")


class ChapterQuery(BaseModel):
    """章节查询参数"""
    book: str = Field(..., description="书名：西游记/三国演义/红楼梦/水浒传")
    chapter: Optional[int] = Field(default=None, description="回号，不传则返回目录", examples=[1])
