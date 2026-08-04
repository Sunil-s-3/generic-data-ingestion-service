"""Ingestion and data query API routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import IngestedRecord, IngestionJob
from app.db.session import get_db
from app.schemas.ingest import (
    IngestRequest,
    IngestResponse,
    JobResponse,
    RecordResponse,
)
from app.services.ingestion import IngestionService

router = APIRouter(tags=["ingestion"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest data from one or more public API URLs",
)
async def ingest_data(
    payload: IngestRequest,
    db: Session = Depends(get_db),
) -> IngestResponse:
    """Fetch each URL and store responses in the database.

    Failures for individual URLs do not abort the whole job; each URL is
    reported independently in the response.
    """
    urls = [str(url) for url in payload.urls]
    service = IngestionService(db)
    return await service.ingest_urls(urls)


@router.get(
    "/records",
    response_model=list[RecordResponse],
    summary="List stored ingested records",
)
def list_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    source_url: str | None = Query(None, description="Optional exact source URL filter"),
    db: Session = Depends(get_db),
) -> list[RecordResponse]:
    """Return recently ingested records (newest first)."""
    query = db.query(IngestedRecord)
    if source_url:
        query = query.filter(IngestedRecord.source_url == source_url)

    rows = (
        query.order_by(IngestedRecord.ingested_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_to_record_response(row) for row in rows]


@router.get(
    "/records/{record_id}",
    response_model=RecordResponse,
    summary="Get a single ingested record",
)
def get_record(record_id: int, db: Session = Depends(get_db)) -> RecordResponse:
    """Return one stored record by id."""
    row = db.get(IngestedRecord, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    return _to_record_response(row)


@router.get(
    "/jobs",
    response_model=list[JobResponse],
    summary="List ingestion jobs",
)
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[JobResponse]:
    """Return recent ingestion jobs (newest first)."""
    jobs = (
        db.query(IngestionJob)
        .order_by(IngestionJob.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_to_job_response(job) for job in jobs]


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get a single ingestion job",
)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobResponse:
    """Return one ingestion job by id."""
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _to_job_response(job)


def _to_record_response(row: IngestedRecord) -> RecordResponse:
    try:
        payload = json.loads(row.payload)
    except json.JSONDecodeError:
        payload = row.payload

    return RecordResponse(
        id=row.id,
        source_url=row.source_url,
        status_code=row.status_code,
        content_type=row.content_type,
        payload=payload,
        record_count=row.record_count,
        ingested_at=row.ingested_at,
    )


def _to_job_response(job: IngestionJob) -> JobResponse:
    try:
        urls = json.loads(job.requested_urls)
    except json.JSONDecodeError:
        urls = [job.requested_urls]

    return JobResponse(
        id=job.id,
        requested_urls=urls if isinstance(urls, list) else [str(urls)],
        success_count=job.success_count,
        failure_count=job.failure_count,
        status=job.status,
        created_at=job.created_at,
    )
