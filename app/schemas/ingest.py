"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class IngestRequest(BaseModel):
    """Request body for ingesting one or more public API URLs."""

    urls: list[HttpUrl] = Field(
        ...,
        min_length=1,
        description="One or more public API URLs to fetch and store.",
        examples=[
            [
                "https://jsonplaceholder.typicode.com/posts/1",
                "https://api.github.com/zen",
            ]
        ],
    )


class UrlIngestResult(BaseModel):
    """Per-URL outcome of an ingestion attempt."""

    url: str
    success: bool
    status_code: int | None = None
    record_id: int | None = None
    record_count: int | None = None
    error: str | None = None


class IngestResponse(BaseModel):
    """Summary response for a multi-URL ingestion job."""

    job_id: int
    status: str
    success_count: int
    failure_count: int
    results: list[UrlIngestResult]


class RecordResponse(BaseModel):
    """Stored ingested record returned by the API."""

    id: int
    source_url: str
    status_code: int
    content_type: str | None
    payload: Any
    record_count: int
    ingested_at: datetime

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    """Ingestion job summary."""

    id: int
    requested_urls: list[str]
    success_count: int
    failure_count: int
    status: str
    created_at: datetime


class HealthResponse(BaseModel):
    """Service health payload."""

    status: str
    app: str
    version: str


class ErrorResponse(BaseModel):
    """Standard error body."""

    detail: str
