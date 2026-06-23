from starlette.requests import Request

from app.services.billing.models import WebhookResult, BillingDisabled
from app.services.billing.provider import BillingProvider


async def handle_stripe_webhook(request: Request, provider: BillingProvider) -> WebhookResult:
    """Handle an incoming Stripe webhook from a Starlette request."""
    if provider is None:
        raise BillingDisabled("No billing provider configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    return provider.handle_webhook(payload, sig)
