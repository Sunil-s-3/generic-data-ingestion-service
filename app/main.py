"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import health, ingest
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.session import init_db

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize resources on startup."""
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Generic service that ingests data from arbitrary public APIs "
        "and stores responses in a database without API-specific coupling."
    ),
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(ingest.router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler so unexpected errors return a consistent JSON body."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Simple root redirect hint."""
    return {
        "message": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }
