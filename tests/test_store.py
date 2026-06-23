"""Tests for app.store"""

import pytest
import tempfile
import os
import uuid
from app.store import Store
from app.models import JobStatus, FetchMode


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def store(temp_db, monkeypatch):
    monkeypatch.setattr("app.config.SQLITE_PATH", temp_db)
    s = Store()
    s.ensure_schema()
    return s


def test_store_initialize_schema(store):
    with store._get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
    assert "scan_sessions" in tables
    assert "scanned_casts" in tables
    assert "delete_jobs" in tables
    assert "delete_logs" in tables


def test_scan_session_crud(store):
    session_id = store.scan_session_create(
        fid=123,
        count=150,
        mode=FetchMode.ALL,
        include_recasts=False,
    )
    assert session_id is not None

    retrieved = store.scan_session_get(session_id)
    assert retrieved is not None
    assert retrieved["fid"] == 123

    store.scan_session_update_status(session_id, "completed")
    updated = store.scan_session_get(session_id)
    assert updated["status"] == "completed"


def test_scanned_casts_list_empty(store):
    casts = store.scanned_casts_list("nonexistent-session")
    assert casts == []


def test_scanned_casts_selected_hashes(store):
    hashes = store.scanned_casts_selected_hashes("nonexistent-session")
    assert hashes == set()


def test_add_and_get_job(store):
    job = store.add_job(
        confirmation_phrase="CONFIRM",
        target_hashes=["0xabc", "0xdef"],
        total=2,
    )
    assert job.id is not None
    assert job.status == JobStatus.PREPARED

    retrieved = store.get_job(job.id)
    assert retrieved is not None
    assert retrieved.id == job.id


def test_update_job(store):
    job = store.add_job(
        confirmation_phrase="CONFIRM",
        target_hashes=["0xabc"],
        total=1,
    )
    job.status = JobStatus.RUNNING
    job.deleted = 1
    store.update_job(job)
    updated = store.get_job(job.id)
    assert updated.status == JobStatus.RUNNING
    assert updated.deleted == 1


def test_confirm_fail_get_set_reset(store):
    uid = str(uuid.uuid4())
    assert store.confirm_fail_get(uid) == 0
    store.confirm_fail_set(uid, 1)
    assert store.confirm_fail_get(uid) == 1
    store.confirm_fail_reset(uid)
    assert store.confirm_fail_get(uid) == 0


def test_audit_events(store):
    uid = str(uuid.uuid4())
    store.add_audit_event(user_id=uid, event_type="cast_deleted", casts_deleted=1)
    count = store.audit_event_count(uid)
    assert count >= 1


def test_add_and_get_logs(store):
    job = store.add_job(
        confirmation_phrase="CONFIRM",
        target_hashes=["0xabc"],
        total=1,
    )
    store.add_log(
        job_id=job.id,
        cast_hash="0xabc",
        status="deleted",
        attempt_count=1,
        response_code=200,
    )
    logs = store.get_logs_for_job(job.id)
    assert len(logs) == 1
    assert logs[0].cast_hash == "0xabc"
