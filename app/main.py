"""FastAPI application entrypoint — routes, SSE, static files, templates."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import ensure_data_dirs, get_settings
from app.models import (
    Cast,
    CastKind,
    ConfigStatus,
    DeleteJob,
    DeleteLog,
    FetchMode,
    FetchRequest,
    FetchResponse,
    JobEvent,
    JobStatus,
    PrepareDeleteRequest,
    PrepareDeleteResponse,
    SessionConfig,
    StartDeleteRequest,
    StopResponse,
)
from app.neynar_client import NeynarClient, get_client
from app.safety import DeleteCheckResult, DeleteRejected, validate_delete_request
from app.services.deletion_service import cancel, confirm_and_start, prepare
from app.services.scan_service import ScanSession, create_session, fetch_casts_for_session
from app.store import Store

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App / lifespan
# ---------------------------------------------------------------------------

app = FastAPI(title="Farcaster Cleaner", version="0.1.0")

# Static files and templates (after ensure_data_dirs so data/ exists)
ensure_data_dirs()
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR)) if TEMPLATES_DIR.exists() else None

# Store singleton
store = Store()
store.ensure_schema()

# ---------------------------------------------------------------------------
# Auth helpers (stub — wire to your session/JWT provider as needed)
# ---------------------------------------------------------------------------

def _get_session_config(request: Request) -> SessionConfig:
    """Pull session credentials from request state (set by auth middleware)."""
    return SessionConfig(
        api_key=getattr(request.state, "api_key", None),
        signer_uuid=getattr(request.state, "signer_uuid", None),
        fid=getattr(request.state, "fid", None),
    )


async def _require_credentials(sc: SessionConfig = Depends(_get_session_config)) -> SessionConfig:
    """Ensure credentials are present before allowing mutation."""
    if not sc.api_key or not sc.signer_uuid or not sc.fid:
        raise HTTPException(status_code=401, detail="Credentials not set in session")
    return sc


# ---------------------------------------------------------------------------
# Events SSE registry
# ---------------------------------------------------------------------------

_event_subscribers: Dict[str, asyncio.Queue[JobEvent]] = {}


def _publish_event(job_id: str, event: JobEvent) -> None:
    for q in _event_subscribers.values():
        q.put_nowait(event)


# ---------------------------------------------------------------------------
# Casts router
# ---------------------------------------------------------------------------

casts_router = APIRouter(prefix="/api/casts", tags=["casts"])


@casts_router.get("/fetch", response_model=FetchResponse)
async def fetch_casts(
    count: int = Query(default=150, ge=1, le=1000),
    mode: FetchMode = Query(default=FetchMode.ALL),
    include_recasts: bool = Query(default=False),
    sc: SessionConfig = Depends(_get_session_config),
) -> FetchResponse:
    """Fetch casts for the session FID and store them in a scan session."""
    settings = get_settings()
    client = get_client(
        api_key=sc.api_key or settings.NEYNAR_API_KEY,
        signer_uuid=sc.signer_uuid or settings.NEYNAR_SIGNER_UUID,
        base_url=settings.NEYNAR_BASE_URL,
    )
    if not sc.fid:
        raise HTTPException(status_code=400, detail="FID not set in session")

    # Create a new scan session
    session = await create_session(
        store=store,
        fid=sc.fid,
        count=count,
        mode=mode,
        include_recasts=include_recasts,
    )

    # Fetch casts
    casts = await fetch_casts_for_session(client=client, session=session)

    return FetchResponse(
        fetched=len(casts),
        selected=len([c for c in casts if c.hash in store.scanned_casts_selected_hashes(session.id)]),
        mode=mode,
        include_recasts=include_recasts,
        casts=casts,
    )


@casts_router.post("/select")
async def select_cast(
    session_id: str,
    cast_hash: str,
    sc: SessionConfig = Depends(_get_session_config),
) -> JSONResponse:
    """Select a cast for deletion."""
    store.scanned_casts_set_selected(session_id, cast_hash, selected=True)
    return JSONResponse({"ok": True, "cast_hash": cast_hash, "selected": True})


@casts_router.post("/deselect")
async def deselect_cast(
    session_id: str,
    cast_hash: str,
    sc: SessionConfig = Depends(_get_session_config),
) -> JSONResponse:
    """Deselect a cast from deletion."""
    store.scanned_casts_set_selected(session_id, cast_hash, selected=False)
    return JSONResponse({"ok": True, "cast_hash": cast_hash, "selected": False})


@casts_router.get("/selected")
async def list_selected(
    session_id: str,
    sc: SessionConfig = Depends(_get_session_config),
) -> JSONResponse:
    """Return selected cast hashes for a session."""
    hashes = store.scanned_casts_selected_hashes(session_id)
    return JSONResponse({"session_id": session_id, "selected_hashes": list(hashes)})


# ---------------------------------------------------------------------------
# Delete router
# ---------------------------------------------------------------------------

delete_router = APIRouter(prefix="/api/delete", tags=["delete"])


@delete_router.post("/prepare", response_model=PrepareDeleteResponse)
async def prepare_delete(
    req: PrepareDeleteRequest,
    sc: SessionConfig = Depends(_require_credentials),
) -> PrepareDeleteResponse:
    """Prepare a delete job and return the confirmation phrase."""
    settings = get_settings()
    try:
        result = prepare(
            store=store,
            target_hashes=req.target_hashes,
            confirmation_phrase=None,  # generated inside prepare
            settings=settings,
        )
        return result
    except DeleteRejected as e:
        raise HTTPException(status_code=400, detail=str(e))


@delete_router.post("/start")
async def start_delete(
    req: StartDeleteRequest,
    sc: SessionConfig = Depends(_require_credentials),
) -> JSONResponse:
    """Validate the confirmation phrase and begin the delete job."""
    settings = get_settings()
    try:
        confirm_and_start(
            store=store,
            job_id=req.job_id,
            confirmation_phrase=req.confirmation_phrase,
            settings=settings,
            publish_fn=_publish_event,
        )
        return JSONResponse({"ok": True, "job_id": req.job_id, "status": "running"})
    except DeleteRejected as e:
        raise HTTPException(status_code=400, detail=str(e))


@delete_router.post("/stop")
async def stop_delete(
    job_id: str,
    sc: SessionConfig = Depends(_require_credentials),
) -> StopResponse:
    """Cancel a running or prepared job."""
    cancel(store=store, job_id=job_id)
    job = store.get_job(job_id)
    return StopResponse(
        job_id=job_id,
        status=job.status if job else JobStatus.CANCELLED,
        message="Job cancelled",
    )


@delete_router.get("/events")
async def delete_events(
    job_id: str,
    sc: SessionConfig = Depends(_require_credentials),
) -> StreamingResponse:
    """SSE stream of job events for a delete job."""
    queue: asyncio.Queue[JobEvent] = asyncio.Queue()

    async def event_generator() -> AsyncGenerator[bytes, None]:
        q_id = str(uuid.uuid4())
        _event_subscribers[q_id] = queue
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=60.0)
                yield f"data: {event.model_dump_json()}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {JobEvent(type='ping', job_id=job_id, timestamp=datetime.utcnow(), data={}).model_dump_json()}\n\n"
        finally:
            _event_subscribers.pop(q_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@delete_router.get("/status/{job_id}")
async def delete_status(
    job_id: str,
    sc: SessionConfig = Depends(_require_credentials),
) -> JSONResponse:
    """Return current job status."""
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(job.model_dump())


# ---------------------------------------------------------------------------
# Admin router
# ---------------------------------------------------------------------------

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


@admin_router.get("/jobs")
async def list_jobs(
    sc: SessionConfig = Depends(_require_credentials),
) -> JSONResponse:
    """List all jobs for the current user."""
    jobs = store.list_jobs()
    return JSONResponse({"jobs": [j.model_dump() for j in jobs]})


@admin_router.get("/logs/{job_id}")
async def get_job_logs(
    job_id: str,
    sc: SessionConfig = Depends(_require_credentials),
) -> JSONResponse:
    """Return logs for a specific job."""
    logs = store.get_logs_for_job(job_id)
    return JSONResponse({"logs": [log.model_dump() for log in logs]})


# ---------------------------------------------------------------------------
# Webhooks router (Telegram / public-mode)
# ---------------------------------------------------------------------------

webhooks_router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@webhooks_router.post("/telegram")
async def telegram_webhook(request: Request) -> JSONResponse:
    """Receive and process Telegram webhook updates."""
    from app.bot.telegram_bot import process_update

    body = await request.json()
    await process_update(body)
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Onboarding router (Neynar signer onboarding)
# ---------------------------------------------------------------------------

onboarding_router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@onboarding_router.get("/begin")
async def begin_onboarding(sc: SessionConfig = Depends(_get_session_config)) -> JSONResponse:
    """Begin the Neynar signer onboarding flow."""
    from app.services.signer_onboarding import begin_onboarding as _begin

    result = await _begin(sc.api_key)
    return JSONResponse(result)


@onboarding_router.post("/confirm")
async def confirm_onboarding(
    signer_uuid: str,
    sc: SessionConfig = Depends(_get_session_config),
) -> JSONResponse:
    """Confirm the Neynar signer onboarding."""
    from app.services.signer_onboarding import confirm_onboarding as _confirm

    result = await _confirm(sc.api_key, signer_uuid)
    return JSONResponse(result)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@ app.get("/health")
async def health_check() -> JSONResponse:
    """Basic health check endpoint."""
    return JSONResponse({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


# ---------------------------------------------------------------------------
# Mount sub-routers
# ---------------------------------------------------------------------------

app.include_router(casts_router)
app.include_router(delete_router)
app.include_router(admin_router)
app.include_router(webhooks_router)
app.include_router(onboarding_router)


# ---------------------------------------------------------------------------
# Root / index
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> Response:
    """Serve the web UI index page if templates are available."""
    if templates is None:
        return JSONResponse({"message": "Farcaster Cleaner API", "version": "0.1.0"})
    return templates.TemplateResponse("index.html", {"request": request})
