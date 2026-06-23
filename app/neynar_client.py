"""Neynar API client for fetching and deleting casts."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.models import Cast, CastKind, FetchMode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class NeynarError(Exception):
    """Base exception for Neynar API errors."""

    def __init__(self, message: str, code: Optional[int] = None) -> None:
        super().__init__(message)
        self.code = code


class NeynarRateLimitError(NeynarError):
    """Raised when Neynar rate limit is exceeded (429)."""
    pass


class NeynarNotFoundError(NeynarError):
    """Raised when a resource is not found (404)."""
    pass


class NeynarAuthError(NeynarError):
    """Raised when authentication fails (401/403)."""
    pass


class NeynarServerError(NeynarError):
    """Raised when Neynar returns a 5xx error."""
    pass


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class NeynarClient:
    """Typed client for the Neynar v2 REST API."""

    def __init__(
        self,
        api_key: str,
        signer_uuid: str,
        base_url: str = "https://api.neynar.com",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._signer_uuid = signer_uuid
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def close(self) -> None:
        self._http.close()

    # ---------------------------------------------------------------------------
# Cast fetching
    # ---------------------------------------------------------------------------

    def fetch_casts_by_fid(
        self,
        fid: int,
        count: int = 150,
        mode: FetchMode = FetchMode.ALL,
        include_recasts: bool = False,
    ) -> List[Cast]:
        """Fetch casts for a given FID using the Neynar user casts endpoint."""
        params: Dict[str, Any] = {
            "fid": fid,
            "limit": min(count, 1000),
        }
        # mode is applied client-side in filter_casts
        url = f"{self._base_url}/v2/farcaster/casts"
        resp = self._handle_response(self._http.get(url, params=params))
        raw_casts: List[Dict[str, Any]] = resp.get("casts", [])
        casts = [self._cast_from_dict(c) for c in raw_casts]
        return self.filter_casts(casts, mode, include_recasts)

    def _cast_from_dict(self, d: Dict[str, Any]) -> Cast:
        """Convert a Neynar API dict to our Cast model."""
        # Neynar v2 cast shape
        hash_str = d.get("hash") or d.get("cast_hash") or ""
        parent = d.get("parent_cast_hash") or d.get("parent_hash") or None
        root = d.get("root_parent_hash") or None
        text = d.get("text", "")
        timestamp_str = d.get("timestamp") or d.get("created_at") or None
        fid = d.get("author", {}).get("fid", 0)
        kind_raw = d.get("type", "").lower()
        url = d.get("link", None)

        # Determine kind
        if kind_raw in ("cast", "root"):
            kind = CastKind.ROOT
        elif kind_raw in ("reply", "thread"):
            kind = CastKind.REPLY
        elif kind_raw == "recast":
            kind = CastKind.RECAST
        else:
            kind = CastKind.UNKNOWN

        return Cast(
            hash=hash_str,
            fid=fid,
            text=text,
            timestamp=timestamp_str,
            parent_hash=parent,
            root_parent_hash=root,
            url=url,
            kind=kind,
            raw_json=d,
        )

    def filter_casts(
        self,
        casts: List[Cast],
        mode: FetchMode,
        include_recasts: bool,
    ) -> List[Cast]:
        """Filter casts according to fetch mode and recast policy."""
        result: List[Cast] = []
        for cast in casts:
            if not include_recasts and cast.kind == CastKind.RECAST:
                continue
            if mode == FetchMode.ROOT_ONLY and cast.kind == CastKind.REPLY:
                continue
            if mode == FetchMode.REPLIES_ONLY and cast.kind == CastKind.ROOT:
                continue
            result.append(cast)
        return result

    # ---------------------------------------------------------------------------
# Cast deletion
    # ---------------------------------------------------------------------------

    def delete_cast(self, cast_hash: str) -> Dict[str, Any]:
        """Delete a cast using the authenticated signer."""
        url = f"{self._base_url}/v2/farcaster/cast"
        payload = {
            "signer_uuid": self._signer_uuid,
            "cast_hash": cast_hash,
        }
        resp = self._handle_response(
            self._http.delete(url, json=payload)
        )
        return resp

    # ---------------------------------------------------------------------------
# HTTP helpers
    # ---------------------------------------------------------------------------

    def _handle_response(self, resp: httpx.Response) -> Dict[str, Any]:
        """Validate response and return JSON body or raise a typed error."""
        status = resp.status_code
        try:
            body = resp.json()
        except Exception:
            body = {}

        if status == 200 or status == 201:
            return body
        if status == 401 or status == 403:
            raise NeynarAuthError(
                f"Neynar auth error: {body.get('message', 'Unknown')}",
                code=status,
            )
        if status == 404:
            raise NeynarNotFoundError(
                f"Neynar resource not found: {body.get('message', 'Unknown')}",
                code=status,
            )
        if status == 429:
            raise NeynarRateLimitError(
                f"Neynar rate limit exceeded: {body.get('message', 'Too Many Requests')}",
                code=status,
            )
        if status >= 500:
            raise NeynarServerError(
                f"Neynar server error: {body.get('message', 'Internal Error')}",
                code=status,
            )
        raise NeynarError(
            f"Neynar API error ({status}): {body.get('message', resp.text[:200])}",
            code=status,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_client(
    api_key: str,
    signer_uuid: str,
    base_url: str = "https://api.neynar.com",
) -> NeynarClient:
    """Build a NeynarClient from credentials."""
    return NeynarClient(api_key=api_key, signer_uuid=signer_uuid, base_url=base_url)
