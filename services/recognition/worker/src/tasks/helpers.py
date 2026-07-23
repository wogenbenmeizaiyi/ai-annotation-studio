import io
from urllib.parse import urlparse

from PIL import Image

from core.config import config
from core.public_security import download_public_image


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
    response = download_public_image(url, headers)

    content_type = response.headers.get("Content-Type", "")
    if content_type and not content_type.lower().startswith("image/"):
        raise ValueError(f"downloaded content is not an image: {content_type}")
    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > config.PUBLIC_MAX_UPLOAD_BYTES:
        response.close()
        raise ValueError("downloaded image exceeds size limit")

    path = parsed.path
    ext = "jpg"
    if "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
            ext = "jpg"

    content = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        content.extend(chunk)
        if len(content) > config.PUBLIC_MAX_UPLOAD_BYTES:
            response.close()
            raise ValueError("downloaded image exceeds size limit")
    response.close()
    return Image.open(io.BytesIO(content)).convert("RGB"), ext


def _image_to_bytes(img: Image.Image) -> bytes:
    """将 PIL Image 对象转为 JPEG 字节流"""
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
