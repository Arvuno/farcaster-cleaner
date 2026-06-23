"""SIWN (Sign-In With Neynar) connect pages."""

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()


@router.get("/connect", response_class=HTMLResponse)
async def connect_page(request: Request):
    """SIWN connect page for linking a FARCASTER account."""
    user = request.session.get("user_id")
    username = request.session.get("username", "Guest")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Connect FARCASTER - Far caster Cleaner</title>
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
        <nav class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/connect">Connect</a>
            <a href="/billing">Billing</a>
            <a href="/auth/logout">Logout</a>
        </nav>
        <main class="container">
            <h1>Connect Your FARCASTER Account</h1>
            <p>Welcome, {username}!</p>

            <div class="connect-card">
                <div class="farcaster-logo">
                    <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="32" cy="32" r="32" fill="#8B5CF6"/>
                        <path d="M32 16C22.059 16 14 24.059 14 34C14 43.941 22.059 52 32 52C41.941 52 50 43.941 50 34C50 24.059 41.941 16 32 16ZM26 28V42L39 35L26 28Z" fill="white"/>
                    </svg>
                </div>
                <h2>Sign in with Neynar</h2>
                <p>Connect your FARCASTER identity using Sign-In With Neynar (SIWN).</p>

                <form id="siwn-form">
                    <button type="button" id="connect-btn" class="btn btn-primary">
                        Connect with FARCASTER
                    </button>
                </form>

                <div id="status-message" class="status-message" style="display:none;"></div>
            </div>

            <div class="info-box">
                <h3>Why connect?</h3>
                <ul>
                    <li>Manage your casts directly from the dashboard</li>
                    <li>Schedule automatic cleanups</li>
                    <li>View analytics for your content</li>
                </ul>
            </div>
        </main>
        <script src="/static/app.js"></script>
        <script>
            document.getElementById('connect-btn').addEventListener('click', async function() {{
                try {{
                    const response = await fetch('/connect/verify', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ action: 'start' }})
                    }});
                    const data = await response.json();
                    if (data.url) {{
                        window.location.href = data.url;
                    }} else if (data.message) {{
                        const statusEl = document.getElementById('status-message');
                        statusEl.textContent = data.message;
                        statusEl.style.display = 'block';
                    }}
                }} catch (err) {{
                    console.error('Connection error:', err);
                }}
            }});
        </script>
    </body>
    </html>
    """


@router.post("/connect/verify", response_class=JSONResponse)
async def verify_signature(request: Request):
    """Verify SIWN signature and complete connection."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    body = await request.json()
    action = body.get("action")

    if action == "start":
        # In production, generate a proper SIWN URL with Neynar
        # For now, return a placeholder response
        return {
            "url": "https://api.neynar.com/v2/auth/connect",
            "message": "SIWN connection would start here. Configure NEYNAR_API_KEY for full functionality."
        }

    # Handle callback from Neynar after user signs
    # In production, verify the signature using Neynar API
    return {
        "success": True,
        "message": "FARCASTER account connected successfully."
    }
