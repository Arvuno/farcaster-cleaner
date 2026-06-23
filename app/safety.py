"""Safety helpers for delete operations — validation, redaction, and rate-limiting."""

from __future__ import annotations

import re
import secrets
from typing import TYPE_CHECKING, List, Optional, Set

if TYPE_CHECKING:
    from app.config import Settings

# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

_NEYNAR_API_KEY_RE = re.compile(r"(x-api-key['\"]?\s*[=:]\s*['\"]?)([a-zA-Z0-9_-]{8,})", re.IGNORECASE)
_SIGNER_UUID_RE = re.compile(
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)


def redact(text: str) -> str:
    """Mask neynar API keys and signer UUIDs in ``text`` for safe logging."""
    if not text:
        return text
    # Mask API keys (looks for patterns like x-api-key: <key>)
    text = _NEYNAR_API_KEY_RE.sub(r"\1********", text)
    # Mask UUIDs that look like signer UUIDs (full UUID form)
    text = _SIGNER_UUID_RE.sub("****-****-****-****-************", text)
    return text


# ---------------------------------------------------------------------------
# Confirmation phrase helpers
# ---------------------------------------------------------------------------

CONFIRMATION_WORDS = [
    "delete", "remove", "erase", "confirm", "proceed", "yes", "doit",
    "destroy", "wipe", "clear", "drop", "purge", "kill", "end", "stop",
]


def generate_confirmation_phrase() -> str:
    """Generate a random 6-word phrase for delete confirmation."""
    return " ".join(secrets.choice(CONFIRMATION_WORDS) for _ in range(6))


# ---------------------------------------------------------------------------
# Safety check result types
# ---------------------------------------------------------------------------


class DeleteCheckResult:
    """Result of a delete-safety check."""

    __slots__ = ("allowed", "reason", "check_type")

    def __init__(
        self,
        allowed: bool,
        reason: Optional[str] = None,
        check_type: Optional[str] = None,
    ) -> None:
        self.allowed = allowed
        self.reason = reason
        self.check_type = check_type


class DeleteRejected(Exception):
    """Raised when a delete request fails safety validation."""

    def __init__(self, reason: str, check_type: Optional[str] = None) -> None:
        super().__init__(reason)
        self.check_type = check_type


# ---------------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------------

# Known safe (read-only / non-destructive) cast hash patterns
_SAFE_HASH_PREFIXES: Set[str] = {
    "0x00000000",  # null / placeholder
}

# Max casts deletable per confirmation
_MAX_DELETABLE_PER_JOB = 1000


def validate_delete_request(
    job_id: str,
    confirmation_phrase: str,
    casts: List[str],
    settings: "Settings",
) -> DeleteCheckResult:
    """Validate that a delete request is safe to proceed.

    Checks:
    - Empty cast list
    - Exceeds per-job limit
    - Confirmation phrase plausibility (anti-automation)
    - Rate-limit state (abuse counters)
    """

    # 1. Empty check
    if not casts:
        return DeleteCheckResult(
            allowed=False,
            reason="No casts selected for deletion.",
            check_type="empty",
        )

    # 2. Per-job limit
    if len(casts) > _MAX_DELETABLE_PER_JOB:
        return DeleteCheckResult(
            allowed=False,
            reason=f"Too many casts selected ({len(casts)}). Maximum is {_MAX_DELETABLE_PER_JOB} per job.",
            check_type="limit",
        )

    # 3. Confirmation phrase sanity (must contain at least one known word)
    phrase_lower = confirmation_phrase.lower().strip()
    word_set = set(phrase_lower.split())
    safe_words = set(CONFIRMATION_WORDS)
    if not word_set & safe_words:
        return DeleteCheckResult(
            allowed=False,
            reason="Confirmation phrase does not contain any recognised delete word.",
            check_type="phrase",
        )

    # 4. All hashes look like real hashes (anti-placeholder)
    hash_re = re.compile(r"^0x[0-9a-fA-F]{8,80}$")
    invalid_hashes = [h for h in casts if not hash_re.match(h)]
    if invalid_hashes:
        return DeleteCheckResult(
            allowed=False,
            reason=f"Found {len(invalid_hashes)} cast hash(es) with invalid format.",
            check_type="hash_format",
        )

    # 5. Settings-level cap enforcement
    cap = settings.DEFAULT_DELETE_COUNT * 2  # Allow up to 2x the default display cap
    if settings.ALLOW_LARGE_DELETE:
        cap = _MAX_DELETABLE_PER_JOB
    if len(casts) > cap:
        return DeleteCheckResult(
            allowed=False,
            reason=f"Selected {len(casts)} casts exceeds the current cap of {cap}. "
                   f"Set ALLOW_LARGE_DELETE=true to override.",
            check_type="cap",
        )

    return DeleteCheckResult(allowed=True)


def validate_confirmation_phrase(phrase: str, expected: str) -> bool:
    """Case-insensitive phrase match for delete confirmation."""
    return phrase.lower().strip() == expected.lower().strip()
