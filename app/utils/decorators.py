"""Route guards: login_required, admin_required, guest_only."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import abort, flash, redirect, request, url_for

from app.extensions import current_user, is_admin


def login_required(view: Callable) -> Callable:
    """Redirect anonymous visitors to the login page, keeping the target."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view: Callable) -> Callable:
    """Allow admins only. Students get a 403 page, not a silent redirect."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please log in with an admin account.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if not is_admin():
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def guest_only(view: Callable) -> Callable:
    """Keep logged-in users away from login/register pages."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user:
            if user.get("role") == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("student.dashboard"))
        return view(*args, **kwargs)

    return wrapped


def safe_next_url(candidate: str | None, fallback_endpoint: str = "student.dashboard") -> str:
    """
    Only allow same-site relative redirects (prevents open redirect abuse).
    """
    if not candidate:
        return url_for(fallback_endpoint)
    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return url_for(fallback_endpoint)
