try:
    import stripe
except ImportError:
    stripe = None

BillingDisabled = stripe is None
