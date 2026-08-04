"""Orchestrates fetching API data and persisting it generically."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import IngestedRecord, IngestionJob
from app.schemas.ingest import IngestResponse, UrlIngestResult
from app.services.fetcher import ApiFetcher, FetchResult

logger = get_logger(__name__)


def _serialize_payload(body: Any) -> str:
    """Serialize arbitrary API payloads to a JSON string for storage."""
    if isinstance(body, str):
        try:
            # Keep already-JSON strings as-is when valid; otherwise wrap as JSON string.
            json.loads(body)
            return body
        except json.JSONDecodeError:
            return json.dumps(body)
    return json.dumps(body)


def _count_records(body: Any) -> int:
    """Estimate how many logical records were returned."""
    if isinstance(body, list):
        return len(body)
    if isinstance(body, dict):
        return 1
    if isinstance(body, str):
        stripped = body.strip()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return len(parsed)
            except json.JSONDecodeError:
                pass
        return 1 if stripped else 0
    return 1


class IngestionService:
    """Coordinates multi-URL ingestion into the database."""

    def __init__(self, db: Session, fetcher: ApiFetcher | None = None) -> None:
        self.db = db
        self.fetcher = fetcher or ApiFetcher()

    async def ingest_urls(self, urls: list[str]) -> IngestResponse:
        """Fetch and store data for each URL, recording per-URL success/failure."""
        unique_urls = list(dict.fromkeys(urls))
        logger.info("Starting ingestion job for %s URL(s)", len(unique_urls))

        job = IngestionJob(
            requested_urls=json.dumps(unique_urls),
            success_count=0,
            failure_count=0,
            status="running",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        fetch_results = await self.fetcher.fetch_many(unique_urls)
        results: list[UrlIngestResult] = []
        success_count = 0
        failure_count = 0

        for fetch in fetch_results:
            result = self._persist_fetch(fetch)
            results.append(result)
            if result.success:
                success_count += 1
            else:
                failure_count += 1

        if failure_count == 0:
            status = "completed"
        elif success_count == 0:
            status = "failed"
        else:
            status = "partial"

        job.success_count = success_count
        job.failure_count = failure_count
        job.status = status
        self.db.commit()
        self.db.refresh(job)

        logger.info(
            "Ingestion job %s finished: status=%s success=%s failure=%s",
            job.id,
            status,
            success_count,
            failure_count,
        )

        return IngestResponse(
            job_id=job.id,
            status=status,
            success_count=success_count,
            failure_count=failure_count,
            results=results,
        )

    def _persist_fetch(self, fetch: FetchResult) -> UrlIngestResult:
        """Persist a successful fetch; return a failure result otherwise."""
        if not fetch.success:
            return UrlIngestResult(
                url=fetch.url,
                success=False,
                status_code=fetch.status_code,
                error=fetch.error or "Fetch failed",
            )

        try:
            record_count = _count_records(fetch.body)
            record = IngestedRecord(
                source_url=fetch.url,
                status_code=fetch.status_code or 0,
                content_type=fetch.content_type,
                payload=_serialize_payload(fetch.body),
                record_count=record_count,
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            logger.info("Stored record id=%s from %s", record.id, fetch.url)
            return UrlIngestResult(
                url=fetch.url,
                success=True,
                status_code=fetch.status_code,
                record_id=record.id,
                record_count=record_count,
            )
        except Exception as exc:  # noqa: BLE001 - keep ingestion resilient
            self.db.rollback()
            logger.exception("Failed to persist data from %s", fetch.url)
            return UrlIngestResult(
                url=fetch.url,
                success=False,
                status_code=fetch.status_code,
                error=f"Persistence error: {exc}",
            )
