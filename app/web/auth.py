"""Web authentication helpers."""

from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse

# In-memory session storage (in production, use Redis or similar)
_session_store: dict[int, dict] = {}


def get_auth_context(request: Request) -> dict:
    """Return the current auth context from the session.

    Returns a dict with user_id and username if authenticated,
    or None values if not.
    """
    user_id = request.session.get("user_id")
    username = request.session.get("username")
    return {
        "user_id": user_id,
        "username": username,
        "authenticated": user_id is not None,
    }


def require_auth(request: Request) -> dict:
    """Extract and validate the user from the session.

    Raises HTTPException 401 if not authenticated.
    Returns the user dict with user_id and username.
    """
    context = get_auth_context(request)
    if not context["authenticated"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return context


def login_user(request: Request, user_id: int, username: str) -> None:
    """Store user in the session."""
    request.session["user_id"] = user_id
    request.session["username"] = username


def logout_user(request: Request) -> None:
    """Clear the user from the session."""
    request.session.pop("user_id", None)
    request.session.pop("username", None)
