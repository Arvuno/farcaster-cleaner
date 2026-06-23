"""Tests for app.models"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from app.models import (
    FetchMode,
    JobStatus,
    CastKind,
    Cast,
    DeleteJob,
    DeleteLog,
    FetchRequest,
    FetchResponse,
    PrepareDeleteRequest,
    PrepareDeleteResponse,
    StartDeleteRequest,
    StopResponse,
    JobEvent,
)


def test_fetch_mode_enum():
    assert FetchMode.ALL == "all"
    assert FetchMode.ROOT_ONLY == "root_only"
    assert FetchMode.REPLIES_ONLY == "replies_only"


def test_job_status_enum():
    assert JobStatus.PREPARED == "prepared"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"
    assert JobStatus.CANCELLED == "cancelled"


def test_cast_kind_enum():
    assert CastKind.ROOT == "root"
    assert CastKind.REPLY == "reply"
    assert CastKind.RECAST == "recast"
    assert CastKind.UNKNOWN == "unknown"


def test_cast_model():
    cast = Cast(
        hash="0xabc123",
        fid=123,
        text="Hello world",
        kind=CastKind.ROOT,
    )
    assert cast.hash == "0xabc123"
    assert cast.fid == 123
    assert cast.text == "Hello world"
    assert cast.kind == CastKind.ROOT


def test_delete_job_model():
    job = DeleteJob(
        id="job-123",
        status=JobStatus.PREPARED,
        total=10,
        deleted=0,
        confirmation_phrase="CONFIRM",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert job.id == "job-123"
    assert job.total == 10
    assert job.status == JobStatus.PREPARED


def test_delete_log_model():
    log = DeleteLog(
        id=1,
        job_id="job-123",
        cast_hash="0xabc",
        status="deleted",
        attempt_count=1,
        timestamp=datetime.now(),
    )
    assert log.job_id == "job-123"
    assert log.status == "deleted"


def test_fetch_request_defaults():
    req = FetchRequest()
    assert req.count == 150
    assert req.mode == FetchMode.ALL
    assert req.include_recasts is False


def test_fetch_request_custom():
    req = FetchRequest(count=500, mode=FetchMode.ROOT_ONLY, include_recasts=True)
    assert req.count == 500
    assert req.mode == FetchMode.ROOT_ONLY
    assert req.include_recasts is True


def test_fetch_request_count_bounds():
    with pytest.raises(ValidationError):
        FetchRequest(count=0)
    with pytest.raises(ValidationError):
        FetchRequest(count=1001)


def test_prepare_delete_request():
    req = PrepareDeleteRequest(target_hashes=["0xabc", "0xdef"])
    assert len(req.target_hashes) == 2


def test_start_delete_request():
    req = StartDeleteRequest(job_id="job-123", confirmation_phrase="CONFIRM")
    assert req.job_id == "job-123"


def test_stop_response():
    resp = StopResponse(job_id="job-123", status=JobStatus.CANCELLED, message="Cancelled")
    assert resp.job_id == "job-123"


def test_job_event():
    event = JobEvent(
        type="progress",
        job_id="job-123",
        timestamp=datetime.now(),
        data={"deleted": 5, "total": 10},
    )
    assert event.type == "progress"
    assert event.data["deleted"] == 5
