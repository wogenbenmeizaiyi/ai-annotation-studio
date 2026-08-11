from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CocoLicense:
    """COCO 许可证信息"""

    id: int = 0
    name: str = ""
    url: Optional[str] = None


@dataclass
class CocoCategory:
    """COCO 类别信息"""

    id: int = 0
    name: str = ""
    supercategory: str = ""

    def to_coco_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "supercategory": self.supercategory}

    @classmethod
    def from_coco_dict(cls, data: Dict[str, Any]) -> "CocoCategory":
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            supercategory=data.get("supercategory", ""),
        )


@dataclass
class CocoImage:
    """COCO 图像信息"""

    id: int = 0
    file_name: str = ""
    width: int = 0
    height: int = 0
    license: Optional[int] = None
    flickr_url: Optional[str] = None
    coco_url: Optional[str] = None
    date_captured: Optional[str] = None

    def to_coco_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "file_name": self.file_name,
        }

        if self.license is not None:
            data["license"] = self.license
        if self.flickr_url:
            data["flickr_url"] = self.flickr_url
        if self.coco_url:
            data["coco_url"] = self.coco_url
        if self.date_captured:
            data["date_captured"] = self.date_captured

        return data

    @classmethod
    def from_coco_dict(cls, data: Dict[str, Any]) -> "CocoImage":
        return cls(
            id=data.get("id", 0),
            file_name=data.get("file_name", ""),
            width=data.get("width", 0),
            height=data.get("height", 0),
            license=data.get("license"),
            flickr_url=data.get("flickr_url"),
            coco_url=data.get("coco_url"),
            date_captured=data.get("date_captured"),
        )


class CocoAnnotation:
    """COCO 标注信息（保持你原来的设计）"""

    def __init__(
        self,
        ann_id: int = 0,
        image_id: int = 0,
        category_id: int = 0,
        bbox: Optional[List[float]] = None,
        segmentation: Optional[Union[List[List[float]], List[float]]] = None,
        iscrowd: int = 0,
    ):
        self.id = ann_id
        self.image_id = image_id
        self.category_id = category_id
        self.bbox = bbox
        self.segmentation = segmentation
        self.iscrowd = iscrowd
        self.area = self._compute_area()

    def _compute_area(self) -> float:
        if self.segmentation:
            return self._polygon_area(self.segmentation)
        if self.bbox:
            _, _, w, h = self.bbox
            return float(w * h)
        return 0.0

    def _polygon_area(self, polygons: List[List[float]]) -> float:
        total_area = 0.0
        for poly in polygons:
            if len(poly) < 6:
                continue
            pts = [(poly[i], poly[i + 1]) for i in range(0, len(poly), 2)]
            area = 0.0
            for i in range(len(pts)):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % len(pts)]
                area += x1 * y2 - x2 * y1
            total_area += abs(area) / 2.0
        return total_area

    def to_coco_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "image_id": self.image_id,
            "category_id": self.category_id,
            "iscrowd": self.iscrowd,
            "area": self.area,
        }

        if self.bbox is not None:
            data["bbox"] = self.bbox

        if self.segmentation is not None:
            data["segmentation"] = self.segmentation

        return data

    @classmethod
    def from_coco_dict(cls, data: Dict[str, Any]) -> "CocoAnnotation":
        return cls(
            ann_id=data.get("id", 0),
            image_id=data.get("image_id", 0),
            category_id=data.get("category_id", 0),
            bbox=data.get("bbox"),
            segmentation=data.get("segmentation"),
            iscrowd=data.get("iscrowd", 0),
        )


class CocoDataset:
    """完整的 COCO 数据集"""

    def __init__(
        self,
        info: Optional[Dict[str, Any]] = None,
        licenses: Optional[List[CocoLicense]] = None,
        categories: Optional[List[CocoCategory]] = None,
        images: Optional[List[CocoImage]] = None,
        annotations: Optional[List[CocoAnnotation]] = None,
    ):
        self.info = info or self._default_info()
        self.licenses = licenses or []
        self.categories = categories or []
        self.images = images or []
        self.annotations = annotations or []

    def _default_info(self) -> Dict[str, Any]:
        """默认数据集信息"""
        return {
            "year": datetime.now().year,
            "version": "1.0",
            "description": "COCO format dataset",
            "contributor": "",
            "url": "",
            "date_created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @classmethod
    def create_default(
        cls, file_name: str = "", width: int = 0, height: int = 0
    ) -> "CocoDataset":
        """创建默认数据集"""
        coco_image = CocoImage(file_name=file_name, width=width, height=height)
        coco_dataset = CocoDataset(images=[coco_image])
        return coco_dataset

    def add_category(self, category: CocoCategory):
        """添加类别"""
        self.categories.append(category)

    def add_image(self, image: CocoImage):
        """添加图像"""
        self.images.append(image)

    def add_annotation(self, annotation: CocoAnnotation):
        """添加标注"""
        self.annotations.append(annotation)

    def get_annotations_by_image_id(self, image_id: int) -> List[CocoAnnotation]:
        """根据图像ID获取标注"""
        return [ann for ann in self.annotations if ann.image_id == image_id]

    def get_category_by_id(self, category_id: int) -> Optional[CocoCategory]:
        """根据类别ID获取类别"""
        for cat in self.categories:
            if cat.id == category_id:
                return cat
        return None

    def get_image_by_id(self, image_id: int) -> Optional[CocoImage]:
        """根据图像ID获取图像"""
        for img in self.images:
            if img.id == image_id:
                return img
        return None

    def to_coco_dict(self) -> Dict[str, Any]:
        """导出为完整的 COCO JSON 格式"""
        return {
            "info": self.info,
            "licenses": [
                {"id": lic.id, "name": lic.name, "url": lic.url}
                for lic in self.licenses
                if lic.url or lic.name or lic.id
            ],
            "categories": [cat.to_coco_dict() for cat in self.categories],
            "images": [img.to_coco_dict() for img in self.images],
            "annotations": [ann.to_coco_dict() for ann in self.annotations],
        }

    @classmethod
    def from_coco_dict(cls, data: Dict[str, Any]) -> "CocoDataset":
        """从 COCO JSON 创建完整数据集"""
        # 解析类别
        categories = [
            CocoCategory.from_coco_dict(cat_data)
            for cat_data in data.get("categories", [])
        ]

        # 解析图像
        images = [
            CocoImage.from_coco_dict(img_data) for img_data in data.get("images", [])
        ]

        # 解析标注
        annotations = [
            CocoAnnotation.from_coco_dict(ann_data)
            for ann_data in data.get("annotations", [])
        ]

        # 解析许可证
        licenses = [
            CocoLicense(
                id=lic_data.get("id", 0),
                name=lic_data.get("name", ""),
                url=lic_data.get("url"),
            )
            for lic_data in data.get("licenses", [])
        ]

        return cls(
            info=data.get("info"),
            licenses=licenses,
            categories=categories,
            images=images,
            annotations=annotations,
        )

    def validate(self) -> List[str]:
        """验证数据集的完整性"""
        errors = []

        # 检查类别ID唯一性
        category_ids = [cat.id for cat in self.categories]
        if len(set(category_ids)) != len(category_ids):
            errors.append("类别ID不唯一")

        # 检查图像ID唯一性
        image_ids = [img.id for img in self.images]
        if len(set(image_ids)) != len(image_ids):
            errors.append("图像ID不唯一")

        # 检查标注ID唯一性
        ann_ids = [ann.id for ann in self.annotations]
        if len(set(ann_ids)) != len(ann_ids):
            errors.append("标注ID不唯一")

        # 检查标注引用
        for ann in self.annotations:
            # 检查引用的图像是否存在
            if ann.image_id not in image_ids:
                errors.append(f"标注 {ann.id} 引用了不存在的图像ID: {ann.image_id}")

            # 检查引用的类别是否存在
            if ann.category_id not in category_ids:
                errors.append(f"标注 {ann.id} 引用了不存在的类别ID: {ann.category_id}")

        return errors
