"""Delete job UI pages."""

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

# In-memory job store (in production, use database)
_jobs = {}


@router.get("/delete", response_class=HTMLResponse)
async def delete_ui(request: Request):
    """Delete UI page for selecting casts to delete."""
    user = request.session.get("user_id")
    username = request.session.get("username", "Guest")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Delete Casts - Far caster Cleaner</title>
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
        <nav class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/delete">Delete</a>
            <a href="/connect">Connect</a>
            <a href="/auth/logout">Logout</a>
        </nav>
        <main class="container">
            <h1>Delete Casts</h1>
            <p>Welcome, {username}!</p>

            <div class="delete-form">
                <form id="fetch-form">
                    <div class="form-group">
                        <label for="count">Number of casts to fetch:</label>
                        <input type="number" id="count" name="count" value="150" min="1" max="1000">
                    </div>

                    <div class="form-group">
                        <label for="mode">Filter mode:</label>
                        <select id="mode" name="mode">
                            <option value="all">All casts</option>
                            <option value="root_only">Root casts only</option>
                            <option value="replies_only">Replies only</option>
                        </select>
                    </div>

                    <div class="form-group checkbox">
                        <label>
                            <input type="checkbox" id="include_recasts" name="include_recasts">
                            Include recasts
                        </label>
                    </div>

                    <button type="submit" class="btn btn-primary">Fetch Casts</button>
                </form>
            </div>

            <div id="casts-list" class="casts-list" style="display:none;"></div>
            <div id="loading" class="loading" style="display:none;">Loading...</div>
        </main>
        <script src="/static/app.js"></script>
    </body>
    </html>
    """


@router.get("/delete/{job_id}", response_class=HTMLResponse)
async def job_status_page(request: Request, job_id: str):
    """Job status page showing progress of a delete job."""
    user = request.session.get("user_id")
    username = request.session.get("username", "Guest")

    # In production, fetch job from database
    job_data = {
        "id": job_id,
        "status": "running",
        "total": 100,
        "deleted": 45,
        "failed": 2,
        "skipped": 3,
    }

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Job {job_id} - Far caster Cleaner</title>
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
        <nav class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/delete">Delete</a>
            <a href="/auth/logout">Logout</a>
        </nav>
        <main class="container">
            <h1>Delete Job Status</h1>
            <p>Welcome, {username}!</p>

            <div class="job-status-card">
                <div class="job-header">
                    <span class="job-id">Job ID: {job_id}</span>
                    <span class="job-status-badge running">Running</span>
                </div>

                <div class="progress-section">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {job_data['deleted']/job_data['total']*100}%"></div>
                    </div>
                    <div class="progress-stats">
                        <span>Deleted: {job_data['deleted']}/{job_data['total']}</span>
                        <span>Failed: {job_data['failed']}</span>
                        <span>Skipped: {job_data['skipped']}</span>
                    </div>
                </div>

                <div class="job-actions">
                    <form action="/delete/{job_id}/cancel" method="post">
                        <button type="submit" class="btn btn-danger">Cancel Job</button>
                    </form>
                </div>
            </div>

            <div class="logs-section">
                <h2>Recent Activity</h2>
                <div class="log-entries">
                    <p class="log-entry">[{new Date().toLocaleTimeString()}] Processing cast 0x1234... deleted</p>
                    <p class="log-entry">[{new Date().toLocaleTimeString()}] Processing cast 0x5678... failed (rate limited)</p>
                    <p class="log-entry">[{new Date().toLocaleTimeString()}] Processing cast 0x9abc... skipped (already deleted)</p>
                </div>
            </div>
        </main>
        <script src="/static/app.js"></script>
    </body>
    </html>
    """


@router.post("/delete/{job_id}/cancel", response_class=HTMLResponse)
async def cancel_job(request: Request, job_id: str):
    """Cancel a running delete job."""
    user = request.session.get("user_id")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # In production, update job status in database
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Job Cancelled</title>
    </head>
    <body>
        <h1>Job {job_id} has been cancelled.</h1>
        <a href="/dashboard">Return to Dashboard</a>
    </body>
    </html>
    """
