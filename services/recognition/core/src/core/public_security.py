import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
from fastapi import HTTPException, Request
from redis import Redis

from core.config import config


PUBLIC_ENDPOINT_GROUPS = {
    ("POST", "/api/recognition/recognize"): "submit",
    ("POST", "/api/recognition/recognize/yolo-detection"): "submit",
    ("POST", "/api/recognition/recognize/yolo-segmentation"): "submit",
    ("POST", "/api/recognition/recognize/sam-segmentation"): "submit",
    ("POST", "/api/recognition/recognize/multimodal"): "submit",
    ("POST", "/api/project/recognize"): "submit",
    ("GET", "/api/recognition/result"): "query",
    ("GET", "/api/recognition/tasks/coco"): "query",
    ("GET", "/api/project/combination"): "query",
    ("POST", "/api/recognition/recognize/direct"): "direct",
    ("POST", "/api/recognition/recognize/direct/yolo-detection"): "direct",
    ("POST", "/api/recognition/recognize/direct/yolo-segmentation"): "direct",
    ("POST", "/api/recognition/recognize/direct/sam-segmentation"): "direct",
    ("POST", "/api/recognition/recognize/direct/multimodal"): "direct",
}

_redis = Redis.from_url(config.AUTH_STATE_REDIS_URL, decode_responses=True)


def public_group(method: str, path: str) -> str | None:
    return PUBLIC_ENDPOINT_GROUPS.get((method.upper(), path.rstrip("/") or "/"))


def request_ip(request: Request) -> str:
    if config.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if forwarded:
            return forwarded
        real_ip = request.headers.get("X-Real-IP", "").strip()
        if real_ip:
            return real_ip
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request, group: str) -> None:
    limit = {
        "submit": config.PUBLIC_SUBMIT_RATE,
        "direct": config.PUBLIC_DIRECT_RATE,
        "query": config.PUBLIC_QUERY_RATE,
    }[group]
    key = f"public-rate:{group}:{request_ip(request)}"
    current = _redis.incr(key)
    if current == 1:
        _redis.expire(key, 60)
    if current > limit:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试")


def _host_allowed(hostname: str) -> bool:
    value = hostname.rstrip(".").lower()
    return any(value == item or value.endswith(f".{item}") for item in config.PUBLIC_IMAGE_URL_ALLOWLIST)


def validate_public_image_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="图片地址只允许 HTTP/HTTPS")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="图片地址不能包含用户凭据")
    if _host_allowed(parsed.hostname):
        return
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
            )
        }
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="图片地址无法解析") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise HTTPException(status_code=400, detail="图片地址不能指向内网或保留地址")


def validate_public_images(images: list[str]) -> None:
    if not images:
        raise HTTPException(status_code=400, detail="图片列表不能为空")
    if len(images) > config.PUBLIC_MAX_IMAGES:
        raise HTTPException(
            status_code=413,
            detail=f"单次最多提交 {config.PUBLIC_MAX_IMAGES} 张图片",
        )
    for url in images:
        validate_public_image_url(url)


def download_public_image(url: str, headers: dict[str, str]) -> requests.Response:
    current = url
    for _ in range(5):
        validate_public_image_url(current)
        response = requests.get(
            current,
            headers=headers,
            timeout=(5, 30),
            stream=True,
            allow_redirects=False,
        )
        if response.is_redirect:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise ValueError("redirect response has no location")
            current = urljoin(current, location)
            continue
        response.raise_for_status()
        return response
    raise ValueError("too many image redirects")
