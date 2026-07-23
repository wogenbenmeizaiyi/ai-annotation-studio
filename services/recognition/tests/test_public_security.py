import socket

import pytest
from fastapi import HTTPException

from core.public_security import public_group, validate_public_image_url


def test_public_routes_use_exact_method_and_path() -> None:
    assert public_group("POST", "/api/recognition/recognize") == "submit"
    assert public_group("GET", "/api/recognition/tasks/coco") == "query"
    assert public_group("GET", "/api/recognition/tasks") is None
    assert public_group("GET", "/api/recognition/tasks/results") is None
    assert public_group("POST", "/api/models") is None


def test_public_image_url_rejects_private_address(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    )
    with pytest.raises(HTTPException) as error:
        validate_public_image_url("http://images.example.test/example.jpg")
    assert error.value.status_code == 400


def test_public_image_url_allows_public_address(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )
    validate_public_image_url("https://images.example.test/example.jpg")
