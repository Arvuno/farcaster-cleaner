"""Tests for app.safety"""

import pytest
from app.safety import (
    redact,
    validate_delete_request,
    DeleteCheckResult,
    DeleteRejected,
)
from app.models import Cast, CastKind, JobStatus, DeleteJob
from datetime import datetime


def test_redact_api_key():
    text = "Using API key sk_abc123xyz"
    redacted = redact(text)
    assert "sk_abc123xyz" not in redacted
    assert "***" in redacted


def test_redact_signer_uuid():
    text = "Signer 12345678-1234-1234-1234-123456789abc used"
    redacted = redact(text)
    assert "12345678-1234-1234-1234-123456789abc" not in redacted


def test_redact_no_secrets():
    text = "Hello world, nothing to hide here"
    redacted = redact(text)
    assert redacted == text


def test_redact_empty():
    assert redact("") == ""
    assert redact(None) == ""


def test_validate_delete_request_empty_hashes():
    result = validate_delete_request(
        job_id="job-1",
        confirmation_phrase="CONFIRM",
        casts=[],
        settings=None,
    )
    assert result.allowed is False
    assert result.check_type == "empty"


def test_validate_delete_request_no_phrase():
    result = validate_delete_request(
        job_id="job-1",
        confirmation_phrase="",
        casts=[Cast(hash="0xabc", fid=1, text="test", kind=CastKind.ROOT)],
        settings=None,
    )
    assert result.allowed is False


def test_delete_check_result_dataclass():
    result = DeleteCheckResult(allowed=True, reason=None)
    assert result.allowed is True
    assert result.reason is None
    assert result.check_type is None


def test_delete_check_result_with_reason():
    result = DeleteCheckResult(allowed=False, reason="Too many casts", check_type="limit")
    assert result.allowed is False
    assert result.reason == "Too many casts"
    assert result.check_type == "limit"
