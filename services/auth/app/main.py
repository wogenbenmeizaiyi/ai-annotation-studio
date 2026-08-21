import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.api.routes import router
from app.core.config import settings
from app.core.dependencies import AuthenticatedUser, get_super_admin
from app.core.redis_client import sync_user_state
from app.core.security import ensure_signing_keys
from app.db.database import SessionLocal
from app.models.user import User


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Annotation Studio Auth",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.AUTH_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
)
app.include_router(router)


@app.get("/openapi.json", include_in_schema=False)
def complete_openapi(
    _: AuthenticatedUser = Depends(get_super_admin),
) -> dict:
    return get_openapi(title=app.title, version="1.0.0", routes=app.routes)


@app.get("/docs", include_in_schema=False)
def complete_docs(
    _: AuthenticatedUser = Depends(get_super_admin),
):
    return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "输入内容不符合要求，请检查后重试", "data": None},
    )


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def startup() -> None:
    ensure_signing_keys()
    db = SessionLocal()
    try:
        for user in db.query(User).all():
            sync_user_state(user)
    finally:
        db.close()
    logger.info("Authentication service ready")
