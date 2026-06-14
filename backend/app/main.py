"""FastAPI application entry point."""

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.router import api_router
from app.config import get_settings
from app.models.response import HealthResponse
from app.utils.logger import configure_logging, configure_sentry


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_sentry(settings)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_prefix)

    @application.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "{} {} -> {} ({:.1f} ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @application.on_event("startup")
    async def startup() -> None:
        redis_status = await _check_redis(settings.redis_url)
        logger.info("API ready. Redis status: {}", redis_status)

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        redis_status = await _check_redis(settings.redis_url)
        chroma_status = await _check_chroma(settings.CHROMA_PERSIST_DIR)
        return HealthResponse(
            status="ok",
            redis=redis_status,
            chroma=chroma_status,
            version=settings.app_version,
        )

    return application


async def _check_redis(redis_url: str) -> str:
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(redis_url, decode_responses=True)
        try:
            await client.ping()
        finally:
            await client.aclose()
        return "ok"
    except Exception as exc:
        return f"error: {exc}"


async def _check_chroma(chroma_path: object) -> str:
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(chroma_path))
        heartbeat = getattr(client, "heartbeat", None)
        if heartbeat is not None:
            heartbeat()
        return "ok"
    except Exception as exc:
        return f"error: {exc}"


app = create_app()

__all__ = ["app", "create_app"]
