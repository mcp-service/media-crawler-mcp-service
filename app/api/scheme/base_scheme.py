from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, TypeVar, Generic, Dict, Any

T = TypeVar("T")


class BasePage(BaseModel):
    pageNum: Optional[int] = Field(default=1, description="当前页码")
    pageSize: Optional[int] = Field(default=10, description="每页数量")
    orderBy: Optional[str] = Field(default="create_time", description="排序字段")


class Page(BasePage, Generic[T]):
    total: int = Field(..., description="总数")
    items: list[T] = Field(..., description="当前页数据列表")


# 通用的list请求，通用逻辑层使用
class ListRequest(BaseModel):
    pageNum: int = Field(default=1, description="当前页码")
    pageSize: int = Field(default=10, description="每页数量")
    orderBy: Optional[Any] = Field(default="create_time", description="排序字段,也可以支持组合排序")
    orderDirection: Optional[str] = Field(default="DESC", description="排序方向，ASC或DESC")

    model_config = ConfigDict(extra="allow")


# 通用的delete请求，通用逻辑层使用
class DeleteRequest(BaseModel):
    id: int| None = Field(default=None, description="id")