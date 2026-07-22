from typing import List, Optional
from pydantic import BaseModel


class CocoCategoryRequest(BaseModel):
    id: Optional[int] = None
    name: str
    supercategory: Optional[str] = ""


class TaskCreateRequest(BaseModel):
    name: str
    detection_type: str
    description: str
    categories: List[CocoCategoryRequest] = []
