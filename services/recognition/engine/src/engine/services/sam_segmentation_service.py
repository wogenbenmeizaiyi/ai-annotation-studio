import logging

import numpy as np
from PIL import Image, ImageDraw

from core.schemas.recognition import RecognitionMethod
from engine.services.sam_base_service import SamBaseService

logger = logging.getLogger(__name__)


class SamSegmentationService(SamBaseService):
    method = RecognitionMethod.SAM_SEGMENTATION

    def __init__(self, *args, **kwargs):
        super().__init__("sam_segmentation", *args, **kwargs)

    def _draw_annotated(
        self, image: Image.Image, items: list[dict], prompts: list[str]
    ) -> Image.Image:
        img_copy = image.copy()
        colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"]

        for idx, item in enumerate(items):
            mask_bool = np.array(item["mask"], dtype=bool)
            color_hex = colors[idx % len(colors)]
            r, g, b = (
                int(color_hex[1:3], 16),
                int(color_hex[3:5], 16),
                int(color_hex[5:7], 16),
            )

            overlay = Image.new("RGBA", img_copy.size, (0, 0, 0, 0))
            overlay_data = np.array(overlay, dtype=np.uint8)
            overlay_data[mask_bool] = [r, g, b, 100]
            overlay_img = Image.fromarray(overlay_data, "RGBA")

            img_copy = img_copy.convert("RGBA")
            img_copy = Image.alpha_composite(img_copy, overlay_img)

        img_copy = img_copy.convert("RGB")
        draw = ImageDraw.Draw(img_copy)
        font_size = max(12, min(image.size) // 40)

        for item in items:
            bbox = item["bbox"]
            label = f"{item['class_name']} {item['confidence']:.2f}"
            draw.text(
                (bbox["x1"], bbox["y1"] - 25), label, fill="white", size=font_size
            )

        return img_copy
