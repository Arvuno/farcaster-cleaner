from abc import ABC, abstractmethod
from app.services.billing.models import CheckoutResult, PortalResult, WebhookResult


class BillingProvider(ABC):
    """Abstract base class for billing providers."""

    @abstractmethod
    def create_checkout(self, user_id: str, price_id: str) -> CheckoutResult:
        """Create a checkout session for a user to upgrade their plan."""
        raise NotImplementedError

    @abstractmethod
    def create_portal(self, user_id: str) -> PortalResult:
        """Create a customer portal session for a user to manage their subscription."""
        raise NotImplementedError

    @abstractmethod
    def handle_webhook(self, payload: bytes, sig: str) -> WebhookResult:
        """Handle an incoming webhook from the billing provider."""
        raise NotImplementedError
