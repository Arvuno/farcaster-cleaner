from dataclasses import dataclass, field
from typing import Optional


class BillingDisabled(Exception):
    """Raised when billing is disabled due to missing stripe package."""
    pass


class BillingConfigurationError(Exception):
    """Raised when billing is misconfigured."""
    pass


@dataclass
class User:
    user_id: str
    plan: str = "free"
    stripe_customer_id: Optional[str] = None


@dataclass
class Plan:
    plan_id: str
    name: str
    price_id: str
    price_monthly: int  # in cents
    features: list[str] = field(default_factory=list)


@dataclass
class CheckoutResult:
    url: str
    session_id: str


@dataclass
class PortalResult:
    url: str


@dataclass
class WebhookResult:
    event_type: str
    processed: bool
    error: Optional[str] = None


def redact_payload(payload: dict) -> dict:
    """Redact sensitive fields from a payload for logging."""
    sensitive_fields = ["card", "cvv", "password", "secret", "token", "authorization"]
    redacted = {}
    for key, value in payload.items():
        if any(field in key.lower() for field in sensitive_fields):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_payload(value)
        else:
            redacted[key] = value
    return redacted
