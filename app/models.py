"""Pydantic models shared across the app."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FetchMode(str, Enum):
    ALL = "all"
    ROOT_ONLY = "root_only"
    REPLIES_ONLY = "replies_only"


class JobStatus(str, Enum):
    PREPARED = "prepared"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CastKind(str, Enum):
    ROOT = "root"
    REPLY = "reply"
    RECAST = "recast"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Cast
# ---------------------------------------------------------------------------


class Cast(BaseModel):
    hash: str
    fid: int
    text: str = ""
    timestamp: Optional[datetime] = None
    parent_hash: Optional[str] = None
    root_parent_hash: Optional[str] = None
    url: Optional[str] = None
    kind: CastKind = CastKind.UNKNOWN
    raw_json: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Delete job
# ---------------------------------------------------------------------------


class DeleteJob(BaseModel):
    id: str
    status: JobStatus = JobStatus.PREPARED
    total: int = 0
    deleted: int = 0
    failed: int = 0
    skipped: int = 0
    created_at: datetime
    updated_at: datetime
    confirmation_phrase: str
    target_hashes: List[str] = Field(default_factory=list)
    backup_path: Optional[str] = None
    last_message: Optional[str] = None
    last_hash: Optional[str] = None


# ---------------------------------------------------------------------------
# Delete log
# ---------------------------------------------------------------------------


class DeleteLog(BaseModel):
    id: int
    job_id: str
    cast_hash: str
    status: str  # "deleted" | "failed" | "skipped" | "already_deleted"
    attempt_count: int
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    timestamp: datetime
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# API request / response DTOs
# ---------------------------------------------------------------------------


class SessionConfig(BaseModel):
    api_key: Optional[str] = None
    signer_uuid: Optional[str] = None
    fid: Optional[int] = None


class ConfigStatus(BaseModel):
    api_key_set: bool
    signer_uuid_set: bool
    fid_set: bool
    api_key_masked: Optional[str] = None
    signer_uuid_masked: Optional[str] = None
    fid: Optional[int] = None


class FetchRequest(BaseModel):
    count: int = Field(default=150, ge=1, le=1000)
    mode: FetchMode = FetchMode.ALL
    include_recasts: bool = False


class FetchResponse(BaseModel):
    fetched: int
    selected: int
    mode: FetchMode
    include_recasts: bool
    casts: List[Cast]


class PrepareDeleteRequest(BaseModel):
    target_hashes: List[str]


class PrepareDeleteResponse(BaseModel):
    job_id: str
    confirmation_phrase: str
    total: int


class StartDeleteRequest(BaseModel):
    job_id: str
    confirmation_phrase: str


class StopResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class JobEvent(BaseModel):
    type: str  # "progress" | "log" | "status" | "done"
    job_id: str
    timestamp: datetime
    data: Dict[str, Any] = Field(default_factory=dict)
