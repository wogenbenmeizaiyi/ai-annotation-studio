import json

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.logging_config import setup_logging
from api.src.routes.project.project import router as project_router
from routes.combination import router as combination_router
from routes.dict import router as dict_router
from routes.model import router as model_router
from routes.recognition import router as recognition_router

setup_logging()

app = FastAPI(title="AI Image Recognition API")


def _standard_response(code: int, message: str, data=None) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def _should_wrap_response(path: str, content_type: str) -> bool:
    if path in {"/docs", "/redoc", "/openapi.json"}:
        return False
    return "application/json" in content_type


def _build_message(status_code: int, payload) -> str:
    if status_code < 400:
        return "success"
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        if detail is not None:
            return str(detail)
    return "request failed"


@app.middleware("http")
async def wrap_api_response(request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if not _should_wrap_response(request.url.path, content_type):
        return response

    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    payload = json.loads(body.decode("utf-8")) if body else None
    if isinstance(payload, dict) and set(payload.keys()) == {"code", "message", "data"}:
        wrapped = payload
    else:
        wrapped = _standard_response(
            response.status_code,
            _build_message(response.status_code, payload),
            payload if response.status_code < 400 else None,
        )

    headers = dict(response.headers)
    headers.pop("content-length", None)
    return JSONResponse(
        content=wrapped,
        status_code=response.status_code,
        headers=headers,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_standard_response(exc.status_code, str(exc.detail), None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_standard_response(422, str(exc.errors()), None),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_standard_response(500, "internal server error", None),
    )


app.include_router(recognition_router, prefix="/api/recognition")
app.include_router(dict_router, prefix="/api/dict")
app.include_router(project_router, prefix="/api/project")
app.include_router(model_router, prefix="/api/models")
app.include_router(combination_router, prefix="/api/combinations")

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=7987, reload=True)
