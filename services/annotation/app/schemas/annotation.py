from typing import List, Optional, Union
from pydantic import BaseModel


class CocoAnnotationSchema(BaseModel):
    id: int
    image_id: int
    category_id: int
    bbox: Optional[List[float]] = None
    segmentation: Optional[Union[List[List[float]], List[float]]] = None
    iscrowd: int = 0
    area: float
