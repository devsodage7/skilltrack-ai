"""
Security helpers: password hashing, CSRF protection, upload validation.

Nothing here depends on MySQL, so it is safe to unit test in isolation.
"""

from __future__ import annotations

import hmac
import re
import secrets
import unicodedata
from pathlib import Path

from flask import abort, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config

CSRF_SESSION_KEY = "_csrf_token"
CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"

PASSWORD_MIN_LENGTH = 8
_SPECIALS = r"""!@#$%^&*()-_=+[]{};:'",.<>/?\|`~"""


# ---------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Create a salted, slow hash. Plaintext is never stored anywhere."""
    return generate_password_hash(password, method=Config.PASSWORD_HASH_METHOD)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Constant-time comparison through Werkzeug. Never raises on bad input."""
    if not password_hash or not password:
        return False
    try:
        return check_password_hash(password_hash, password)
    except (ValueError, TypeError):
        return False


def password_errors(password: str) -> list[str]:
    """Return a list of policy violations (empty list = acceptable)."""
    problems: list[str] = []
    if len(password or "") < PASSWORD_MIN_LENGTH:
        problems.append(f"Use at least {PASSWORD_MIN_LENGTH} characters.")
    if not re.search(r"[A-Z]", password or ""):
        problems.append("Add at least one capital letter.")
    if not re.search(r"[a-z]", password or ""):
        problems.append("Add at least one small letter.")
    if not re.search(r"\d", password or ""):
        problems.append("Add at least one digit.")
    if not any(ch in _SPECIALS for ch in password or ""):
        problems.append("Add at least one special character.")
    if re.search(r"\s", password or ""):
        problems.append("Spaces are not allowed.")
    return problems


# ---------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------
def csrf_token() -> str:
    """Return the token bound to the current session, creating it if needed."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def csrf_protect() -> None:
    """
    Reject state-changing requests without a valid session-bound token.

    Called from a before_request hook in the app factory.
    """
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    if request.endpoint in {"static", "api.health"}:
        return

    sent = request.form.get(CSRF_FORM_FIELD) or request.headers.get(CSRF_HEADER, "")
    expected = session.get(CSRF_SESSION_KEY, "")

    if not expected or not sent or not hmac.compare_digest(str(sent), str(expected)):
        abort(
            400,
            description=(
                "Security token missing or expired. Reload the page and submit "
                "the form again."
            ),
        )


def rotate_session() -> None:
    """Clear the session after login/logout to prevent session fixation."""
    session.clear()
    # A new CSRF token is generated lazily on the next render.


# ---------------------------------------------------------------------
# File uploads
# ---------------------------------------------------------------------
def sanitise_filename(filename: str, fallback: str = "resume.pdf") -> str:
    """
    Keep only a display-safe version of the original name.
    The stored name is always generated separately with UUIDs.
    """
    name = unicodedata.normalize("NFKD", filename or "")
    name = Path(name).name  # strip any directory component
    name = re.sub(r"[^\w\s.\-()]", "", name).strip()
    name = re.sub(r"\s+", " ", name)
    if not name or name in {".", ".."}:
        return fallback
    return name[:255]


def random_stored_name(extension: str = ".pdf") -> str:
    """Server-side filename: 32 hex chars + extension. Never user controlled."""
    ext = extension if extension.startswith(".") else f".{extension}"
    return f"{secrets.token_hex(16)}{ext.lower()}"


def extension_allowed(filename: str) -> bool:
    suffix = Path(filename or "").suffix.lower().lstrip(".")
    return suffix in Config.ALLOWED_EXTENSIONS


def looks_like_pdf(head: bytes) -> bool:
    """Magic byte check - the real defence against a renamed .exe."""
    return bool(head) and head.startswith(Config.PDF_MAGIC_BYTES)


def human_size(num_bytes: int) -> str:
    size = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"
