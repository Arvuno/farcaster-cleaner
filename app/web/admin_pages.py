"""Admin pages."""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse

from app.web.auth import require_auth

router = APIRouter()


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard page."""
    user = require_auth(request)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Dashboard - Far caster Cleaner</title>
        <link rel="stylesheet" href="/static/admin.css">
    </head>
    <body>
        <nav class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/admin">Admin</a>
            <a href="/billing">Billing</a>
            <a href="/auth/logout">Logout</a>
        </nav>
        <main class="container">
            <h1>Admin Dashboard</h1>
            <p>Welcome, {user['username']}!</p>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Users</h3>
                    <p class="stat-value">1,234</p>
                </div>
                <div class="stat-card">
                    <h3>Active Jobs</h3>
                    <p class="stat-value">42</p>
                </div>
                <div class="stat-card">
                    <h3>Revenue (MRR)</h3>
                    <p class="stat-value">$12,450</p>
                </div>
            </div>
            <h2>Quick Actions</h2>
            <div class="actions">
                <a href="/admin/users" class="btn">Manage Users</a>
                <a href="/admin/jobs" class="btn">View Jobs</a>
            </div>
        </main>
    </body>
    </html>
    """


@router.get("/admin/users", response_class=HTMLResponse)
async def user_management(request: Request):
    """User management page."""
    require_auth(request)
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>User Management - Far caster Cleaner</title>
        <link rel="stylesheet" href="/static/admin.css">
    </head>
    <body>
        <nav class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/admin">Admin</a>
            <a href="/billing">Billing</a>
            <a href="/auth/logout">Logout</a>
        </nav>
        <main class="container">
            <h1>User Management</h1>
            <table class="users-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>1</td>
                        <td>alice</td>
                        <td>alice@example.com</td>
                        <td><span class="badge active">Active</span></td>
                        <td>
                            <form action="/admin/users/1/ban" method="post" style="display:inline;">
                                <button type="submit" class="btn-small">Ban</button>
                            </form>
                        </td>
                    </tr>
                    <tr>
                        <td>2</td>
                        <td>bob</td>
                        <td>bob@example.com</td>
                        <td><span class="badge active">Active</span></td>
                        <td>
                            <form action="/admin/users/2/ban" method="post" style="display:inline;">
                                <button type="submit" class="btn-small">Ban</button>
                            </form>
                        </td>
                    </tr>
                </tbody>
            </table>
        </main>
    </body>
    </html>
    """


@router.post("/admin/users/{{user_id}}/ban", response_class=HTMLResponse)
async def ban_user(request: Request, user_id: int):
    """Ban a user."""
    require_auth(request)
    # In production, update the database to ban the user
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>User Banned</title>
    </head>
    <body>
        <h1>User has been banned successfully.</h1>
        <a href="/admin/users">Back to Users</a>
    </body>
    </html>
    """
