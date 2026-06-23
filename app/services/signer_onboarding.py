"""Signer onboarding flow for Neynar custody authentication."""

from enum import Enum

SIGNER_APPROVED = "approved"
SIGNER_FAILED = "failed"
PENDING_APPROVAL = "pending"


class SignerOnboardingError(Exception):
    """Raised when signer onboarding fails."""
    pass


class SignerFidMismatch(Exception):
    """Raised when the signer FID does not match the expected FID."""
    pass


def begin_onboarding(api_key: str, signer_uuid: str) -> str:
    """Begin the signer onboarding flow and return the approval URL.

    Args:
        api_key: Neynar API key.
        signer_uuid: The signer UUID to onboard.

    Returns:
        The approval URL to redirect the user to.
    """
    from app.neynar_client import NeynarClient
    client = NeynarClient(api_key=api_key)
    result = client.create_signer_approval_url(signer_uuid)
    return result.get("url", "")


def confirm_onboarding(signer_uuid: str, api_key: str) -> dict:
    """Confirm that a signer has completed the onboarding flow.

    Args:
        signer_uuid: The signer UUID to confirm.
        api_key: Neynar API key.

    Returns:
        A dict with signer info including status, fid, etc.
    """
    from app.neynar_client import NeynarClient
    client = NeynarClient(api_key=api_key)
    result = client.get_signer(signer_uuid)

    status = result.get("status", "")
    if status != SIGNER_APPROVED:
        raise SignerOnboardingError(f"Signer {signer_uuid} is not approved: {status}")

    return result
