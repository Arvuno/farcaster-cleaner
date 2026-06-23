"""Tests for app.config"""

import pytest
from app.config import (
    Settings,
    get_settings,
    validate_fid,
    validate_cast_hash,
    validate_signer_uuid,
    validate_count,
    is_admin_user,
    get_admin_user_ids,
    PublicModeUnsafe,
    assert_public_mode_safe,
    assert_private_mode_safe,
    generate_webhook_secret,
)


def test_validate_fid_valid():
    assert validate_fid(123) == 123
    assert validate_fid("456") == 456


def test_validate_fid_invalid():
    with pytest.raises(ValueError):
        validate_fid(0)
    with pytest.raises(ValueError):
        validate_fid(-1)
    with pytest.raises(ValueError):
        validate_fid(True)


def test_validate_cast_hash_valid():
    h = validate_cast_hash("0x1234567890abcdef")
    assert h == "0x1234567890abcdef"


def test_validate_cast_hash_invalid():
    with pytest.raises(ValueError):
        validate_cast_hash("")
    with pytest.raises(ValueError):
        validate_cast_hash("not_a_hash")


def test_validate_signer_uuid_valid():
    u = validate_signer_uuid("12345678-1234-1234-1234-123456789abc")
    assert u == "12345678-1234-1234-1234-123456789abc"


def test_validate_count_valid():
    assert validate_count(50) == 50
    assert validate_count(1, lo=1, hi=10) == 1
    assert validate_count(10, lo=1, hi=10) == 10


def test_generate_webhook_secret():
    secret = generate_webhook_secret()
    assert len(secret) == 32
    assert all(c in "0123456789abcdef" for c in secret)


def test_is_admin_user_no_admins():
    # When TELEGRAM_ADMIN_USER_IDS is empty, no one is admin
    assert is_admin_user(123) is False
    assert is_admin_user(None) is False
