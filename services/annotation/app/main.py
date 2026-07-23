import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.image import router as image_router
from app.api.tasks import router as tasks_router
from app.api.annotation import router as annotation_router
from app.api.train_task import router as train_task
from app.api.train_task import train_task_service
from app.api.train_agent import router as train_agent_router
from app.api.sam3 import router as sam3_router
from app.core.config import settings
from app.core.auth import authenticate_request
from app.services.agent.auto_analysis_service import auto_analysis_service


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                "app.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            ),
        ],
    )

    agent_logger = logging.getLogger("agent")
    agent_logger.setLevel(logging.INFO)
    agent_log_path = Path(settings.AGENT_LOG_FILE)
    agent_log_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_agent_log = agent_log_path.resolve()
    has_agent_handler = any(
        isinstance(handler, RotatingFileHandler)
        and Path(handler.baseFilename).resolve() == resolved_agent_log
        for handler in agent_logger.handlers
    )
    if not has_agent_handler:
        agent_handler = RotatingFileHandler(
            agent_log_path,
            maxBytes=settings.AGENT_LOG_MAX_BYTES,
            backupCount=settings.AGENT_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        agent_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        )
        agent_logger.addHandler(agent_handler)
    # 保持向根日志传播，使Agent事件也出现在控制台和app.log中。
    agent_logger.propagate = True
    agent_logger.info(
        "agent_logging_ready model=%s log_file=%s api_key_configured=%s",
        settings.AGENT_MODEL,
        resolved_agent_log,
        bool(settings.AGENT_API_KEY),
    )


def create_app() -> FastAPI:
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("🚀 AI Annotation Service starting...")

    app = FastAPI(title="AI Annotation Service")
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.AUTH_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": str(exc.detail), "data": None},
        )

    @app.middleware("http")
    async def authenticate_requests(request: Request, call_next):
        if request.url.path.startswith("/api") or request.url.path in {
            "/docs",
            "/openapi.json",
            "/redoc",
        }:
            try:
                request.state.auth = authenticate_request(request)
                if request.url.path in {"/docs", "/openapi.json", "/redoc"} and not (
                    request.state.auth.is_super_admin
                ):
                    raise HTTPException(
                        status_code=403,
                        detail="仅超级管理员可查看完整 API 文档",
                    )
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"code": exc.status_code, "message": str(exc.detail), "data": None},
                )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        cost = (time.time() - start) * 1000

        logging.getLogger("request").info(
            "%s %s -> %d (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            cost,
        )
        return response

    # 路由
    app.include_router(image_router, prefix="/api")
    app.include_router(tasks_router, prefix="/api")
    app.include_router(annotation_router, prefix="/api")
    app.include_router(train_task, prefix="/api")
    app.include_router(train_agent_router, prefix="/api")
    app.include_router(sam3_router)

    @app.on_event("startup")
    def start_background_services():
        train_task_service.start_worker()
        recovered_analysis_count = auto_analysis_service.recover_unfinished()
        if recovered_analysis_count:
            logger.info("恢复未完成自动分析数量: %s", recovered_analysis_count)

    @app.on_event("shutdown")
    def stop_background_services():
        train_task_service.stop_worker()

    logger.info("SAM3 模型将按需加载")

    return app


app = create_app()
