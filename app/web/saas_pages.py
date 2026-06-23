"""SaaS dashboard pages."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()


@router.get("/saas/dashboard", response_class=HTMLResponse)
async def saas_dashboard(request: Request):
    """SaaS dashboard showing usage and subscription details."""
    user = request.session.get("user_id")
    username = request.session.get("username", "Guest")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SaaS Dashboard - Far caster Cleaner</title>
        <link rel="stylesheet" href="/static/saas.css">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
        <nav class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/saas/dashboard">SaaS</a>
            <a href="/saas/stats">Stats</a>
            <a href="/billing">Billing</a>
            <a href="/auth/logout">Logout</a>
        </nav>
        <main class="container">
            <h1>SaaS Dashboard</h1>
            <p>Welcome, {username}!</p>

            <div class="saas-grid">
                <div class="saas-card">
                    <h3>Monthly Usage</h3>
                    <div class="usage-bar">
                        <div class="usage-fill" style="width: 45%"></div>
                    </div>
                    <p>45 of 100 casts used</p>
                </div>

                <div class="saas-card">
                    <h3>Subscription</h3>
                    <p class="plan-badge">Pro Plan</p>
                    <p>$9.99/month</p>
                    <a href="/billing" class="btn-small">Manage</a>
                </div>

                <div class="saas-card">
                    <h3>API Calls</h3>
                    <p class="stat-large">1,234</p>
                    <p>this month</p>
                </div>

                <div class="saas-card">
                    <h3>Data Storage</h3>
                    <p class="stat-large">12.5 MB</p>
                    <p>of 100 MB used</p>
                </div>
            </div>

            <div class="saas-section">
                <h2>Recent Activity</h2>
                <table class="activity-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Action</th>
                            <th> casts</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>2026-06-23</td>
                            <td>Delete Job</td>
                            <td>150</td>
                            <td><span class="badge success">Completed</span></td>
                        </tr>
                        <tr>
                            <td>2026-06-22</td>
                            <td>Fetch</td>
                            <td>500</td>
                            <td><span class="badge success">Completed</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </main>
    </body>
    </html>
    """


@router.get("/saas/stats", response_class=HTMLResponse)
async def usage_stats(request: Request):
    """Usage statistics page."""
    user = request.session.get("user_id")
    username = request.session.get("username", "Guest")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Usage Stats - Far caster Cleaner</title>
        <link rel="stylesheet" href="/static/saas.css">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
        <nav class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/saas/dashboard">SaaS</a>
            <a href="/saas/stats">Stats</a>
            <a href="/billing">Billing</a>
            <a href="/auth/logout">Logout</a>
        </nav>
        <main class="container">
            <h1>Usage Statistics</h1>
            <p>Welcome, {username}!</p>

            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Casts Deleted</h3>
                    <p class="stat-value">12,456</p>
                </div>
                <div class="stat-card">
                    <h3>This Month</h3>
                    <p class="stat-value">1,234</p>
                </div>
                <div class="stat-card">
                    <h3>API Calls</h3>
                    <p class="stat-value">45,678</p>
                </div>
                <div class="stat-card">
                    <h3>Success Rate</h3>
                    <p class="stat-value">98.5%</p>
                </div>
            </div>

            <div class="chart-section">
                <h2>Usage Over Time</h2>
                <div class="chart-placeholder">
                    <p>[Chart would render here - integrate a charting library for production]</p>
                </div>
            </div>

            <div class="export-section">
                <h2>Export Data</h2>
                <form action="/saas/stats/export" method="post">
                    <button type="submit" class="btn">Export as CSV</button>
                </form>
            </div>
        </main>
    </body>
    </html>
    """


@router.get("/saas/stats/data", response_class=JSONResponse)
async def stats_json(request: Request):
    """JSON endpoint for usage statistics."""
    user = request.session.get("user_id")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # In production, fetch from database
    return {
        "total_casts_deleted": 12456,
        "this_month": 1234,
        "api_calls": 45678,
        "success_rate": 98.5,
        "subscription_tier": "pro",
    }
