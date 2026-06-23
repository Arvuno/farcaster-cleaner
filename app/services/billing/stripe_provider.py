try:
    import stripe
except ImportError:
    stripe = None

from typing import Optional
import hashlib
import hmac

from app.services.billing.provider import BillingProvider
from app.services.billing.models import (
    BillingConfigurationError,
    BillingDisabled,
    CheckoutResult,
    PortalResult,
    WebhookResult,
    redact_payload,
)


class StripeProvider(BillingProvider):
    """Stripe-based billing provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        success_url: str = "https://example.com/success",
        cancel_url: str = "https://example.com/cancel",
    ):
        if stripe is None:
            raise BillingDisabled("stripe package is required for StripeProvider")

        if not api_key:
            raise BillingConfigurationError("Stripe API key is required")

        stripe.api_key = api_key
        self.webhook_secret = webhook_secret
        self.success_url = success_url
        self.cancel_url = cancel_url

    def create_checkout(self, user_id: str, price_id: str) -> CheckoutResult:
        """Create a Stripe checkout session."""
        try:
            checkout_session = stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=self.success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=self.cancel_url,
                metadata={"user_id": user_id},
            )
            return CheckoutResult(
                url=checkout_session.url,
                session_id=checkout_session.id,
            )
        except stripe.error.StripeError as e:
            raise BillingConfigurationError(f"Failed to create checkout session: {e}")

    def create_portal(self, user_id: str) -> PortalResult:
        """Create a Stripe customer portal session."""
        try:
            # Look up the customer ID for this user
            customers = stripe.Customer.list(email=f"{user_id}@placeholder", limit=1)
            if not customers.data:
                raise BillingConfigurationError(f"No Stripe customer found for user {user_id}")

            customer_id = customers.data[0].id
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=self.success_url,
            )
            return PortalResult(url=portal_session.url)
        except stripe.error.StripeError as e:
            raise BillingConfigurationError(f"Failed to create portal session: {e}")

    def handle_webhook(self, payload: bytes, sig: str) -> WebhookResult:
        """Handle an incoming Stripe webhook."""
        if not self.webhook_secret:
            raise BillingConfigurationError("Webhook secret is not configured")

        try:
            event = stripe.Webhook.construct_event(payload, sig, self.webhook_secret)
        except ValueError:
            return WebhookResult(event_type="invalid", processed=False, error="Invalid payload")
        except stripe.error.SignatureVerificationError:
            return WebhookResult(event_type="invalid", processed=False, error="Invalid signature")

        event_type = event.get("type", "unknown")
        processed = True

        # Process specific event types
        if event_type == "checkout.session.completed":
            # Handle successful checkout
            pass
        elif event_type == "customer.subscription.updated":
            # Handle subscription update
            pass
        elif event_type == "customer.subscription.deleted":
            # Handle subscription deletion
            pass
        elif event_type == "invoice.payment_failed":
            # Handle payment failure
            pass
        else:
            processed = False

        return WebhookResult(event_type=event_type, processed=processed)
