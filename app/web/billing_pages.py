"""Billing pages with optional Stripe integration."""

try:
    import stripe
    from stripe import StripeClient
    HAS_STRIPE = True
except ImportError:
    HAS_STRIPE = False

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

# Stripe price IDs (configure in environment)
STRIPE_PRICE_ID = "price_xxxxxxxxxxxxxxxxxxxx"
STRIPE_WEBHOOK_SECRET = "whsec_xxxxxxxxxxxxxxxxxxxx"


@router.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request):
    """Billing page showing subscription status and options."""
    user = request.session.get("user_id")
    username = request.session.get("username", "Guest")

    if not user:
        return RedirectResponse(url="/auth/login")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Billing - Far caster Cleaner</title>
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
        <nav class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/billing">Billing</a>
            <a href="/auth/logout">Logout</a>
        </nav>
        <main class="container">
            <h1>Billing</h1>
            <p>Welcome, {username}!</p>

            <div class="billing-card">
                <h2>Current Plan</h2>
                <div class="plan-info">
                    <span class="plan-name">Free Tier</span>
                    <span class="plan-price">$0/mo</span>
                </div>
                <ul class="plan-features">
                    <li>50 casts per month</li>
                    <li>Basic support</li>
                    <li>Single account</li>
                </ul>
            </div>

            <div class="billing-card">
                <h2>Upgrade to Pro</h2>
                <div class="plan-info">
                    <span class="plan-name">Pro</span>
                    <span class="plan-price">$9.99/mo</span>
                </div>
                <ul class="plan-features">
                    <li>Unlimited casts</li>
                    <li>Priority support</li>
                    <li>Multiple accounts</li>
                    <li>Advanced analytics</li>
                </ul>
                <form action="/billing/checkout" method="post">
                    <button type="submit" class="btn btn-primary">Upgrade Now</button>
                </form>
            </div>
        </main>
    </body>
    </html>
    """


@router.post("/billing/checkout", response_class=HTMLResponse)
async def create_checkout(request: Request):
    """Create a Stripe checkout session."""
    user = request.session.get("user_id")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if not HAS_STRIPE:
        return """
        <!DOCTYPE html>
        <html lang="en">
        <body>
            <h1>Stripe not configured</h1>
            <p>Please set STRIPE_API_KEY in your environment.</p>
            <a href="/billing">Back to Billing</a>
        </body>
        </html>
        """

    try:
        stripe.api_key = "sk_test_xxxx"
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }],
            mode="subscription",
            success_url="/billing?success=true",
            cancel_url="/billing?canceled=true",
        )
        return RedirectResponse(url=checkout_session.url)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/billing/portal", response_class=HTMLResponse)
async def create_portal(request: Request):
    """Create a Stripe customer portal session."""
    user = request.session.get("user_id")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if not HAS_STRIPE:
        return """
        <!DOCTYPE html>
        <html lang="en">
        <body>
            <h1>Stripe not configured</h1>
            <p>Please set STRIPE_API_KEY in your environment.</p>
            <a href="/billing">Back to Billing</a>
        </body>
        </html>
        """

    try:
        stripe.api_key = "sk_test_xxxx"
        portal_session = stripe.billing_portal.Session.create(
            customer="cus_xxxx",
            return_url="/billing",
        )
        return RedirectResponse(url=portal_session.url)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/billing/webhook", response_class=HTMLResponse)
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    if not HAS_STRIPE:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stripe not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Process successful checkout
        pass
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        # Process subscription cancellation
        pass

    return JSONResponse(content={"received": True})
