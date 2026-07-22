import io
from urllib.parse import urlparse

import requests
from PIL import Image


IMAGE_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def download_image(url: str) -> tuple[Image.Image, str]:
    """从 URL 下载图片并返回 PIL Image 对象和文件扩展名"""
    parsed = urlparse(url)
    headers = {
        **IMAGE_REQUEST_HEADERS,
        "Referer": f"{parsed.scheme}://{parsed.netloc}/",
    }
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    if content_type and not content_type.lower().startswith("image/"):
        raise ValueError(f"downloaded content is not an image: {content_type}")

    path = parsed.path
    ext = "jpg"
    if "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
            ext = "jpg"

    return Image.open(io.BytesIO(response.content)).convert("RGB"), ext


def _image_to_bytes(img: Image.Image) -> bytes:
    """将 PIL Image 对象转为 JPEG 字节流"""
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
