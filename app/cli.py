"""CLI entrypoint for the Far caster Cleaner application.

Usage:
    python -m app.cli validate   # Validate configuration
    python -m app.cli fetch      # Fetch casts dry-run style
    python -m app.cli serve      # Run the FastAPI server with uvicorn
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

import click
import uvicorn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug: bool) -> None:
    """Farcaster Cleaner CLI."""
    _setup_logging(logging.DEBUG if debug else logging.INFO)


@cli.command("validate")
def validate() -> None:
    """Validate the application configuration.

    Checks:
    - Required environment variables / .env
    - Database directory is writable
    - Neynar credentials look valid
    """
    from app.config import ensure_data_dirs, get_settings

    click.echo("Validating configuration ...")
    errors: list[str] = []

    # 1. Ensure data dirs
    try:
        ensure_data_dirs()
        click.echo("  [OK] Data directories created/verified")
    except Exception as exc:
        errors.append(f"  [FAIL] Cannot create data directories: {exc}")

    # 2. Load settings
    try:
        settings = get_settings()
        click.echo("  [OK] Settings loaded")
    except Exception as exc:
        errors.append(f"  [FAIL] Cannot load settings: {exc}")
        click.echo(click.style("Validation FAILED", fg="red"))
        sys.exit(1)

    # 3. Neynar credentials
    if not settings.NEYNAR_API_KEY:
        errors.append("  [WARN] NEYNAR_API_KEY is not set")
    else:
        click.echo("  [OK] NEYNAR_API_KEY is configured")

    if not settings.NEYNAR_SIGNER_UUID:
        errors.append("  [WARN] NEYNAR_SIGNER_UUID is not set")
    else:
        click.echo("  [OK] NEYNAR_SIGNER_UUID is configured")

    if not settings.FARCASTER_FID:
        errors.append("  [WARN] FARCASTER_FID is not set")
    else:
        click.echo(f"  [OK] FARCASTER_FID is configured: {settings.FARCASTER_FID}")

    # 4. Report
    if errors:
        for err in errors:
            click.echo(click.style(err, fg="yellow"))
    else:
        click.echo(click.style("Configuration is valid", fg="green"))


@cli.command("fetch")
@click.option("--count", default=10, help="Number of casts to fetch")
@click.option("--mode", default="all", help="Fetch mode: all, root_only, replies_only")
@click.option("--include-recasts", is_flag=True, help="Include recasts")
def fetch(count: int, mode: str, include_recasts: bool) -> None:
    """Fetch casts dry-run style (prints to stdout, does not delete)."""
    from app.config import ensure_data_dirs, get_settings
    from app.models import FetchMode
    from app.neynar_client import get_client

    _setup_logging()

    ensure_data_dirs()
    settings = get_settings()

    if not settings.NEYNAR_API_KEY:
        click.echo(click.style("Error: NEYNAR_API_KEY is not set", fg="red"))
        sys.exit(1)
    if not settings.NEYNAR_SIGNER_UUID:
        click.echo(click.style("Error: NEYNAR_SIGNER_UUID is not set", fg="red"))
        sys.exit(1)
    if not settings.FARCASTER_FID:
        click.echo(click.style("Error: FARCASTER_FID is not set", fg="red"))
        sys.exit(1)

    try:
        fetch_mode = FetchMode(mode)
    except ValueError:
        click.echo(click.style(f"Invalid mode: {mode}", fg="red"))
        sys.exit(1)

    client = get_client(
        api_key=settings.NEYNAR_API_KEY,
        signer_uuid=settings.NEYNAR_SIGNER_UUID,
        base_url=settings.NEYNAR_BASE_URL,
    )

    click.echo(f"Fetching {count} casts for FID {settings.FARCASTER_FID} (mode={fetch_mode.value}) ...")
    try:
        casts = client.fetch_casts_by_fid(
            fid=settings.FARCASTER_FID,
            count=count,
            mode=fetch_mode,
            include_recasts=include_recasts,
        )
        click.echo(f"Fetched {len(casts)} casts:\n")
        for cast in casts:
            kind_str = f"[{cast.kind.value}]" if cast.kind else ""
            ts = cast.timestamp.isoformat() if cast.timestamp else "?"
            click.echo(f"  {cast.hash} {kind_str} {ts}")
            if cast.text:
                text_preview = cast.text[:80] + ("..." if len(cast.text) > 80 else "")
                click.echo(f"    {text_preview}")
        click.echo(click.style(f"\nDry-run complete: {len(casts)} casts fetched", fg="green"))
    except Exception as exc:
        click.echo(click.style(f"Fetch failed: {exc}", fg="red"))
        sys.exit(1)


@cli.command("dry-run")
@click.argument("cast_hashes", nargs=-1, required=True)
def dry_run(cast_hashes: tuple[str, ...]) -> None:
    """Simulate deletion of the given cast hashes (no actual API calls)."""
    from app.models import CastKind, DeleteJob, JobStatus
    from datetime import datetime

    click.echo(f"Dry-run: would delete {len(cast_hashes)} casts\n")
    for h in cast_hashes:
        click.echo(f"  [WOULD DELETE] {h}")
    click.echo(click.style(f"\nDry-run complete: {len(cast_hashes)} casts would be deleted", fg="green"))


@cli.command("serve")
@click.option("--host", default=None, help="Host to bind")
@click.option("--port", default=None, type=int, help="Port to bind")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--workers", default=1, type=int, help="Number of worker processes")
@click.option("--log-level", default="info", help="Uvicorn log level")
def serve(
    host: Optional[str],
    port: Optional[int],
    reload: bool,
    workers: int,
    log_level: str,
) -> None:
    """Start the FastAPI application with uvicorn."""
    from app.config import ensure_data_dirs, get_settings

    ensure_data_dirs()
    settings = get_settings()

    h = host or settings.HOST
    p = port or settings.PORT

    click.echo(f"Starting server on {h}:{p} (workers={workers}, reload={reload})")

    uvicorn.run(
        "app.main:app",
        host=h,
        port=p,
        reload=reload,
        workers=workers,
        log_level=log_level,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
