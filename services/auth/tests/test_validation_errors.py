import asyncio
import json
from typing import cast

from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.main import validation_exception_handler


def test_validation_error_response_does_not_echo_submitted_password() -> None:
    submitted_password = "12345678"
    error = RequestValidationError(
        [
            {
                "type": "string_too_short",
                "loc": ("body", "password"),
                "msg": "String should have at least 12 characters",
                "input": submitted_password,
                "ctx": {"min_length": 12},
            }
        ]
    )

    response = asyncio.run(validation_exception_handler(cast(Request, None), error))
    payload = json.loads(response.body)

    assert response.status_code == 422
    assert payload == {
        "code": 422,
        "message": "输入内容不符合要求，请检查后重试",
        "data": None,
    }
    assert submitted_password not in response.body.decode()
    assert "input" not in response.body.decode()
