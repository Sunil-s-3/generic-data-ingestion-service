"""Basic unit tests for payload helpers and schemas."""

import json

from app.schemas.ingest import IngestRequest
from app.services.ingestion import _count_records, _serialize_payload


def test_serialize_dict_payload():
    assert json.loads(_serialize_payload({"a": 1})) == {"a": 1}


def test_serialize_list_payload():
    assert json.loads(_serialize_payload([1, 2, 3])) == [1, 2, 3]


def test_count_records_list():
    assert _count_records([{"id": 1}, {"id": 2}]) == 2


def test_count_records_dict():
    assert _count_records({"id": 1}) == 1


def test_ingest_request_requires_urls():
    req = IngestRequest(urls=["https://example.com/api"])
    assert len(req.urls) == 1
