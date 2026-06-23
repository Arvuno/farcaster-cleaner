"""Application configuration loaded from environment / .env / config.local.json.

Precedence (highest to lowest):
  1. Web UI session values (in-memory, set via ``/api/config/session``)
  2. ``config.local.json`` (project root)
  3. ``.env`` (project root) or process env
  4. Built-in defaults

Pydantic settings + python-dotenv. No secrets are logged; accessors return
plain values but the application always treats them as sensitive.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


# Project root = parent of the app/ directory.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
BACKUP_DIR: Path = DATA_DIR / "backups"
LOG_DIR: Path = DATA_DIR / "logs"
SQLITE_PATH: Path = DATA_DIR / "farcaster_cleaner.sqlite"

# Local config (per-machine, gitignored). JSON format. Optional.
CONFIG_LOCAL_PATH: Path = PROJECT_ROOT / "config.local.json"

# Field names that are secrets. We never export these by default; we never
# log them; we never persist them to SQLite.
SECRET_FIELD_NAMES = frozenset({"neynar_api_key", "NEYNAR_API_KEY",
                                "neynar_signer_uuid", "NEYNAR_SIGNER_UUID"})


# ---------------------------------------------------------------------------
# Source tracking
# ---------------------------------------------------------------------------


class ConfigSource(str, Enum):
    """Where a value came from, in precedence order."""

    WEB_SESSION = "web_session"
    CONFIG_LOCAL_JSON = "config.local.json"
    ENV = ".env"
    EMPTY = "empty"


# Ordered from highest to lowest priority.
SOURCE_PRIORITY: List[ConfigSource] = [
    ConfigSource.WEB_SESSION,
    ConfigSource.CONFIG_LOCAL_JSON,
    ConfigSource.ENV,
    ConfigSource.EMPTY,
]


# ---------------------------------------------------------------------------
# Settings (pydantic)
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Runtime configuration.

    Values are loaded from process environment first, then from ``.env`` in
    the project root. ``config.local.json`` is layered on top at runtime by
    :func:`load_local_config_file`. The web UI session can override
    everything in-memory; ``.env`` and ``config.local.json`` are just
    convenient defaults.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Required credentials (placeholders acceptable; resolved per-request) ---
    NEYNAR_API_KEY: Optional[str] = Field(
        default=None, description="Neynar API key (x-api-key header)."
    )
    NEYNAR_SIGNER_UUID: Optional[str] = Field(
        default=None, description="Neynar signer UUID with delete permission."
    )
    FARCASTER_FID: Optional[int] = Field(
        default=None, description="Farcaster FID whose casts to manage."
    )

    # --- Optional tunables ---
    NEYNAR_BASE_URL: str = Field(
        default="https://api.neynar.com", description="Neynar API base URL."
    )
    DELETE_RATE_LIMIT_RPS: float = Field(
        default=1.5, ge=0.1, le=50.0, description="Max delete requests per second."
    )
    DELETE_MAX_ATTEMPTS: int = Field(
        default=3, ge=1, le=10, description="Max attempts per cast (for 429/5xx)."
    )
    HOST: str = Field(default="127.0.0.1")
    PORT: int = Field(default=8132, ge=1, le=65535)

    # --- UI / fetch defaults (overridable from .env / config.local.json) ---
    DEFAULT_DELETE_COUNT: int = Field(
        default=150, ge=1, le=1000, description="Default fetch count in UI."
    )
    DEFAULT_MODE: str = Field(
        default="all", description="Default fetch mode (all/root_only/replies_only)."
    )
    INCLUDE_RECASTS: bool = Field(
        default=False, description="Default include-recasts toggle in UI."
    )
    DELETE_RATE_PER_SECOND: float = Field(
        default=1.5, ge=0.1, le=50.0, description="UI display value for rate."
    )
    ALLOW_LARGE_DELETE: bool = Field(
        default=False, description="Allow delete counts above the default cap."
    )

    # --- Public/SaaS mode ---
    APP_ENV: str = Field(default="local", description="Application environment: local, production.")
    APP_SECRET_KEY: Optional[str] = Field(default=None, description="Fernet encryption key for secrets at rest.")
    PUBLIC_BASE_URL: Optional[str] = Field(default=None, description="Public-facing base URL for webhooks/SaaS.")
    BOT_MODE: str = Field(default="polling", description="Bot dispatch mode: polling or webhook.")

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, description="Telegram bot token from @BotFather.")
    TELEGRAM_ADMIN_USER_IDS: str = Field(default="", description="Comma-separated Telegram user IDs with admin access.")
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Secret for Telegram webhook endpoint.")


# ---------------------------------------------------------------------------
# Public-mode exception
# ---------------------------------------------------------------------------


class PublicModeUnsafe(Exception):
    """Raised when the bot is started in an unsafe public-mode configuration."""

    pass


# ---------------------------------------------------------------------------
# Admin helpers
# ---------------------------------------------------------------------------


def is_admin_user(tg_user_id: Optional[int]) -> bool:
    """Return True if ``tg_user_id`` is in TELEGRAM_ADMIN_USER_IDS."""
    if tg_user_id is None:
        return False
    return tg_user_id in get_admin_user_ids()


def get_admin_user_ids() -> List[int]:
    """Return the list of Telegram admin user IDs from TELEGRAM_ADMIN_USER_IDS."""
    settings = get_settings()
    if not settings.TELEGRAM_ADMIN_USER_IDS:
        return []
    try:
        return [int(x.strip()) for x in settings.TELEGRAM_ADMIN_USER_IDS.split(",") if x.strip()]
    except ValueError:
        return []


# ---------------------------------------------------------------------------
# Mode-safety assertions
# ---------------------------------------------------------------------------


def _is_public_mode() -> bool:
    """Return True if the app is running in public/SaaS mode."""
    settings = get_settings()
    return settings.APP_ENV not in ("local", "")


def assert_public_mode_safe() -> None:
    """Raise PublicModeUnsafe if public mode is misconfigured."""
    if not _is_public_mode():
        return
    settings = get_settings()
    if not settings.PUBLIC_BASE_URL:
        raise PublicModeUnsafe("PUBLIC_BASE_URL is not set; required for public mode.")
    if not settings.APP_SECRET_KEY:
        raise PublicModeUnsafe("APP_SECRET_KEY is not set; required for public mode.")


def assert_private_mode_safe() -> None:
    """Raise PublicModeUnsafe if private mode (local bot) is misconfigured."""
    if _is_public_mode():
        return
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        raise PublicModeUnsafe("TELEGRAM_BOT_TOKEN is not set; cannot start the bot.")


def assert_webhook_mode_safe() -> None:
    """Raise PublicModeUnsafe if webhook mode is misconfigured."""
    settings = get_settings()
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        raise PublicModeUnsafe("TELEGRAM_WEBHOOK_SECRET is not set; required for webhook mode.")
    if not settings.PUBLIC_BASE_URL:
        raise PublicModeUnsafe("PUBLIC_BASE_URL is not set; required for webhook mode.")


def generate_webhook_secret() -> str:
    """Generate a 32-character random secret suitable for TELEGRAM_WEBHOOK_SECRET."""
    return secrets.token_hex(16)


# ---------------------------------------------------------------------------
# Local config (config.local.json)
# ---------------------------------------------------------------------------


# Mapping from JSON keys (snake_case) to .env / settings keys.
_LOCAL_KEY_TO_SETTINGS_KEY: Dict[str, str] = {
    "neynar_api_key": "NEYNAR_API_KEY",
    "neynar_signer_uuid": "NEYNAR_SIGNER_UUID",
    "farcaster_fid": "FARCASTER_FID",
    "neynar_base_url": "NEYNAR_BASE_URL",
    "delete_rate_limit_rps": "DELETE_RATE_LIMIT_RPS",
    "delete_max_attempts": "DELETE_MAX_ATTEMPTS",
    "host": "HOST",
    "port": "PORT",
    "default_delete_count": "DEFAULT_DELETE_COUNT",
    "default_mode": "DEFAULT_MODE",
    "include_recasts": "INCLUDE_RECASTS",
    "delete_rate_per_second": "DELETE_RATE_PER_SECOND",
    "allow_large_delete": "ALLOW_LARGE_DELETE",
}


class LocalConfig(BaseModel):
    """Schema for ``config.local.json`` (snake_case JSON keys)."""

    neynar_api_key: Optional[str] = Field(default=None)
    neynar_signer_uuid: Optional[str] = Field(default=None)
    farcaster_fid: Optional[int] = Field(default=None)
    neynar_base_url: Optional[str] = Field(default=None)
    delete_rate_limit_rps: Optional[float] = Field(default=None)
    delete_max_attempts: Optional[int] = Field(default=None)
    host: Optional[str] = Field(default=None)
    port: Optional[int] = Field(default=None)
    default_delete_count: Optional[int] = Field(default=None)
    default_mode: Optional[str] = Field(default=None)
    include_recasts: Optional[bool] = Field(default=None)
    delete_rate_per_second: Optional[float] = Field(default=None)
    allow_large_delete: Optional[bool] = Field(default=None)

    @field_validator("default_mode")
    @classmethod
    def _check_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ("all", "root_only", "replies_only"):
            raise ValueError("default_mode must be one of all/root_only/replies_only")
        return v

    @field_validator("farcaster_fid")
    @classmethod
    def _check_fid(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError("farcaster_fid must be an integer")
        validate_fid(v)
        return v


def load_local_config_file(path: Optional[Path] = None) -> Optional[LocalConfig]:
    """Read and validate ``config.local.json`` (returns ``None`` if absent)."""
    p = path or CONFIG_LOCAL_PATH
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"config.local.json is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("config.local.json must be a JSON object at the top level")
    try:
        return LocalConfig(**raw)
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"config.local.json schema error: {exc}") from exc


def apply_local_config_to_env(local: LocalConfig) -> List[str]:
    """Push non-empty ``local`` values into ``os.environ`` for the Settings layer."""
    set_keys: List[str] = []
    data = local.model_dump(exclude_none=True)
    for json_key, value in data.items():
        settings_key = _LOCAL_KEY_TO_SETTINGS_KEY.get(json_key)
        if not settings_key:
            continue
        if settings_key in os.environ and os.environ[settings_key]:
            continue
        os.environ[settings_key] = str(value)
        set_keys.append(settings_key)
    return set_keys


# ---------------------------------------------------------------------------
# Safe template export
# ---------------------------------------------------------------------------


def safe_template(include_secrets: bool = False) -> Dict[str, Any]:
    """Return a config.local.json template with secrets blanked by default."""
    settings = get_settings()
    template: Dict[str, Any] = {
        "neynar_api_key": settings.NEYNAR_API_KEY if include_secrets else "",
        "neynar_signer_uuid": settings.NEYNAR_SIGNER_UUID if include_secrets else "",
        "farcaster_fid": settings.FARCASTER_FID,
        "default_delete_count": 150,
        "default_mode": "all",
        "include_recasts": False,
        "delete_rate_per_second": 1.5,
        "allow_large_delete": False,
    }
    return template


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def ensure_data_dirs() -> None:
    """Create the data/ subdirectories if missing. Safe to call repeatedly."""
    for p in (DATA_DIR, BACKUP_DIR, LOG_DIR):
        p.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Settings cache
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    return Settings()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


# A Farcaster cast hash is a 0x-prefixed hex string.
_CAST_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{8,80}$")

# A signer UUID is a standard 8-4-4-4-12 hex UUID.
_SIGNER_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def validate_fid(value: Any) -> int:
    """Validate that ``value`` is a positive integer suitable as an FID."""
    if isinstance(value, bool):
        raise ValueError("fid must be numeric (got bool)")
    if not isinstance(value, int):
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"fid must be numeric (got {type(value).__name__})") from exc
    if value <= 0:
        raise ValueError(f"fid must be a positive integer (got {value})")
    if value > 2**53:
        raise ValueError(f"fid is implausibly large (got {value})")
    return value


def validate_signer_uuid(value: Any) -> str:
    """Validate that ``value`` looks like a Neynar signer UUID."""
    if not isinstance(value, str):
        raise ValueError("signer_uuid must be a string")
    s = value.strip()
    if not s:
        raise ValueError("signer_uuid is empty")
    if not _SIGNER_UUID_RE.match(s):
        raise ValueError("signer_uuid must be a UUID in 8-4-4-4-12 hex form")
    return s


def validate_cast_hash(value: Any) -> str:
    """Validate that ``value`` looks like a Farcaster cast hash."""
    if not isinstance(value, str):
        raise ValueError("cast hash must be a string")
    s = value.strip()
    if not s:
        raise ValueError("cast hash is empty")
    if not _CAST_HASH_RE.match(s):
        raise ValueError("cast hash must be 0x-prefixed hex (8..80 hex chars)")
    return s.lower()


def validate_count(value: Any, *, lo: int = 1, hi: int = 1000) -> int:
    """Validate a fetch count is an integer in the inclusive range ``[lo, hi]``."""
    if isinstance(value, bool):
        raise ValueError("count must be numeric (got bool)")
    if not isinstance(value, int):
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"count must be numeric (got {type(value).__name__})") from exc
    if value < lo or value > hi:
        raise ValueError(f"count must be in [{lo}, {hi}] (got {value})")
    return value


def validate_fid_or_none(value: Any) -> Optional[int]:
    """Like :func:`validate_fid` but returns ``None`` for empty input."""
    if value is None or value == "" or (isinstance(value, str) and not value.strip()):
        return None
    return validate_fid(value)


def validate_count_or_default(value: Any, default: int = 150) -> int:
    """Like :func:`validate_count` but falls back to ``default`` for empty input."""
    if value is None or value == "":
        return default
    return validate_count(value)


# ---------------------------------------------------------------------------
# Source-aware status helper (used by the API layer)
# ---------------------------------------------------------------------------


def collect_sources(
    *,
    session_api_key: Optional[str],
    session_signer_uuid: Optional[str],
    session_fid: Optional[int],
) -> Dict[str, Tuple[Optional[str], ConfigSource]]:
    """Resolve (value, source) for each credential, applying precedence."""
    settings = get_settings()
    local = load_local_config_file()

    def _resolve(
        session_val: Any,
        local_val: Any,
        env_val: Any,
    ) -> Tuple[Optional[str], ConfigSource]:
        if session_val not in (None, "", 0):
            return (str(session_val) if not isinstance(session_val, str) else session_val, ConfigSource.WEB_SESSION)
        if local is not None and local_val not in (None, ""):
            return (str(local_val) if not isinstance(local_val, str) else local_val, ConfigSource.CONFIG_LOCAL_JSON)
        if env_val not in (None, ""):
            return (str(env_val), ConfigSource.ENV)
        return (None, ConfigSource.EMPTY)

    api_key, api_src = _resolve(
        session_api_key,
        local.neynar_api_key if local else None,
        settings.NEYNAR_API_KEY,
    )
    signer, signer_src = _resolve(
        session_signer_uuid,
        local.neynar_signer_uuid if local else None,
        settings.NEYNAR_SIGNER_UUID,
    )
    fid: Optional[int] = None
    fid_src = ConfigSource.EMPTY
    if session_fid:
        fid, fid_src = int(session_fid), ConfigSource.WEB_SESSION
    elif local is not None and local.farcaster_fid:
        fid, fid_src = int(local.farcaster_fid), ConfigSource.CONFIG_LOCAL_JSON
    elif settings.FARCASTER_FID:
        fid, fid_src = int(settings.FARCASTER_FID), ConfigSource.ENV

    return {
        "api_key": (api_key, api_src),
        "signer_uuid": (signer, signer_src),
        "fid": (str(fid) if fid else None, fid_src),
    }
