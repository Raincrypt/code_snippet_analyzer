from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import api_router
from app.config import Settings, get_settings
from app.db import create_engine, create_session_factory
from app.errors import register_error_handlers
from app.logging_config import configure_logging
from app.middleware import RequestContextMiddleware
from app.services.reviewer import build_reviewer


def create_app(settings: Settings | None = None) -> FastAPI:
    """Builds the app. Tests call this with their own settings; uvicorn uses `app` below."""
    settings = settings or get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings.database_url)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        yield
        await engine.dispose()  # close connections cleanly on shutdown

    app = FastAPI(
        title="Code Snippet Analyzer API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.docs_enabled else None,
    )
    app.state.settings = settings
    app.state.reviewer = build_reviewer(settings)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type", "X-Request-ID"],
        )
    # Added last so it is outermost: every request, even CORS preflights, gets an ID and a log line.
    app.add_middleware(RequestContextMiddleware)

    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
