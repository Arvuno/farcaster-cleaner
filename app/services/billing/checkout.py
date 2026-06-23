from app.services.billing.models import CheckoutResult, PortalResult, BillingDisabled
from app.services.billing.provider import BillingProvider


def create_checkout_session(user_id: str, price_id: str, provider: BillingProvider) -> CheckoutResult:
    """Create a checkout session for a user to upgrade their plan."""
    if provider is None:
        raise BillingDisabled("No billing provider configured")
    return provider.create_checkout(user_id, price_id)


def create_portal_session(user_id: str, provider: BillingProvider) -> PortalResult:
    """Create a customer portal session for a user to manage their subscription."""
    if provider is None:
        raise BillingDisabled("No billing provider configured")
    return provider.create_portal(user_id)
