"""Safety gate for signer approval verification before delete operations."""

from app.neynar_client import NeynarClient


class SignerNotApprovedError(Exception):
    """Raised when the signer has not been approved for delete operations."""
    pass


def evaluate_signer_for_delete(signer_uuid: str, api_key: str) -> bool:
    """Evaluate whether a signer is approved for delete operations.

    Args:
        signer_uuid: The Neynar signer UUID.
        api_key: The Neynar API key.

    Returns:
        True if the signer is approved, False otherwise.

    Raises:
        SignerNotApprovedError: If the signer is not approved or not found.
    """
    client = NeynarClient(api_key=api_key)
    signer_info = client.get_signer(signer_uuid)

    status = signer_info.get("status", "")
    if status != "approved":
        raise SignerNotApprovedError(
            f"Signer {signer_uuid} is not approved for delete operations. "
            f"Current status: {status}"
        )

    return True
