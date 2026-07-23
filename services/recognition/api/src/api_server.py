import json
import logging
import time
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from core.auth import authenticate_request
from core.config import config
from core.logging_config import setup_logging
from core.public_security import enforce_rate_limit, public_group, request_ip
from api.src.routes.project.project import router as project_router
from routes.combination import router as combination_router
from routes.dict import router as dict_router
from routes.model import router as model_router
from routes.recognition import router as recognition_router

setup_logging()
logger = logging.getLogger("api.access")

app = FastAPI(
    title="AI Image Recognition API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.PLATFORM_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _standard_response(code: int, message: str, data=None) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def _should_wrap_response(path: str, content_type: str) -> bool:
    if path in {"/docs", "/openapi.json", "/public/docs", "/public/openapi.json"}:
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


@app.middleware("http")
async def enforce_access_boundary(request: Request, call_next):
    path = request.url.path.rstrip("/") or "/"
    requested_method = request.method
    if request.method == "OPTIONS":
        requested_method = request.headers.get("Access-Control-Request-Method", "")
    group = public_group(requested_method, path)
    is_public_docs = path in {"/public/docs", "/public/openapi.json"}

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    if request.method == "OPTIONS" and group:
        response = JSONResponse(content=None, status_code=204)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = requested_method
        response.headers["Access-Control-Allow-Headers"] = request.headers.get(
            "Access-Control-Request-Headers", "Content-Type"
        )
        return response
    try:
        if group:
            enforce_rate_limit(request, group)
        elif not is_public_docs:
            context = authenticate_request(request)
            if path in {"/docs", "/openapi.json"} and not context.is_super_admin:
                raise HTTPException(status_code=403, detail="仅超级管理员可查看完整 API 文档")
            request.state.auth = context
        response = await call_next(request)
    except HTTPException as exc:
        response = JSONResponse(
            status_code=exc.status_code,
            content=_standard_response(exc.status_code, str(exc.detail), None),
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    if group or is_public_docs:
        response.headers["Access-Control-Allow-Origin"] = "*"
        if "Access-Control-Allow-Credentials" in response.headers:
            del response.headers["Access-Control-Allow-Credentials"]
    logger.info(
        "request_id=%s source_ip=%s method=%s path=%s elapsed_ms=%.2f status=%s public_group=%s",
        request_id,
        request_ip(request),
        request.method,
        path,
        (time.perf_counter() - started) * 1000,
        response.status_code,
        group or "protected",
    )
    return response


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


def _public_openapi() -> dict:
    schema = get_openapi(
        title="AI Image Recognition Public API",
        version="1.0.0",
        description="无需平台账号即可调用的检测、状态查询和 COCO 结果接口。",
        routes=app.routes,
    )
    public_paths: dict = {}
    for path, operations in schema.get("paths", {}).items():
        selected = {
            method: operation
            for method, operation in operations.items()
            if public_group(method, path)
        }
        if selected:
            public_paths[path] = selected
    schema["paths"] = public_paths
    return schema


@app.get("/public/openapi.json", include_in_schema=False)
def public_openapi():
    return _public_openapi()


@app.get("/public/docs", include_in_schema=False)
def public_docs():
    return get_swagger_ui_html(
        openapi_url="/public/openapi.json",
        title="AI Image Recognition Public API",
    )


@app.get("/openapi.json", include_in_schema=False)
def complete_openapi():
    return get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )


@app.get("/docs", include_in_schema=False)
def complete_docs():
    return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title)

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=7987, reload=True)
