"""Scan session management and cast fetching."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from app.models import Cast, CastKind, FetchMode
from app.neynar_client import NeynarClient
from app.store import Store


@dataclass
class ScanSession:
    """Represents a scan session for fetching and selecting casts."""

    session_id: str
    fid: int
    casts: List[Cast] = field(default_factory=list)
    selected_hashes: List[str] = field(default_factory=list)
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.utcnow)


def create_session(fid: int, api_key: str, signer_uuid: str) -> ScanSession:
    """Create a new scan session for the given FID."""
    session_id = f"scan_{fid}_{datetime.utcnow().timestamp()}"
    return ScanSession(session_id=session_id, fid=fid)


def fetch_casts_for_session(
    session: ScanSession,
    count: int,
    mode: FetchMode,
    include_recasts: bool,
) -> List[Cast]:
    """Fetch casts for the session using NeynarClient."""
    client = NeynarClient()
    casts = client.fetch_casts(
        fid=session.fid,
        count=count,
        mode=mode,
        include_recasts=include_recasts,
    )
    session.casts = casts
    return casts


def paginate(casts: List[Cast], page: int, per_page: int) -> List[Cast]:
    """Paginate a list of casts."""
    start = (page - 1) * per_page
    end = start + per_page
    return casts[start:end]


def toggle(session_id: str, cast_hash: str) -> None:
    """Toggle selection of a cast in the session."""
    store = Store()
    session = store.get_session(session_id)
    if session is None:
        return

    if cast_hash in session.selected_hashes:
        session.selected_hashes.remove(cast_hash)
    else:
        session.selected_hashes.append(cast_hash)
    store.update_session(session)


def deselect_all(session_id: str) -> None:
    """Deselect all casts in the session."""
    store = Store()
    session = store.get_session(session_id)
    if session is None:
        return

    session.selected_hashes = []
    store.update_session(session)


def update_session_status(session_id: str, status: str) -> None:
    """Update the status of a scan session."""
    store = Store()
    session = store.get_session(session_id)
    if session is None:
        return

    session.status = status
    store.update_session(session)
