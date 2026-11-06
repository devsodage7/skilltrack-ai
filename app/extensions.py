"""
Session bridge between Flask and the database.

This is the only module that knows how a logged-in user is represented in
the session, which keeps blueprints and services free of that detail.
"""

from __future__ import annotations

from flask import g, session

from models import student_model

SESSION_USER_KEY = "user_id"
SESSION_ROLE_KEY = "role"

_MISSING = object()


def login_user(user: dict) -> None:
    """
    Rotate the session (prevents session fixation) and store the identity.
    Call this AFTER any pre-login flash message you want to keep.
    """
    from app.utils.security import rotate_session

    rotate_session()
    session.permanent = True
    session[SESSION_USER_KEY] = int(user["id"])
    session[SESSION_ROLE_KEY] = str(user.get("role") or "student")
    setattr(g, "user", None)


def logout_user() -> None:
    session.clear()
    setattr(g, "user", None)


def current_user() -> dict | None:
    """
    Return the logged-in user row (cached per request) or None.

    A deactivated account is logged out immediately.
    """
    cached = getattr(g, "user", _MISSING)
    if cached is not _MISSING and (cached is None or isinstance(cached, dict)):
        return cached

    user = None
    user_id = session.get(SESSION_USER_KEY)
    if user_id:
        try:
            row = student_model.get_by_id(int(user_id))
        except (TypeError, ValueError):
            row = None

        if row and int(row.get("is_active") or 0) == 1:
            user = row
        else:
            session.clear()

    setattr(g, "user", user)
    return user


def is_admin() -> bool:
    user = current_user()
    return bool(user and user.get("role") == "admin")


def dashboard_endpoint() -> str:
    """Where a user should land after login."""
    return "admin.dashboard" if is_admin() else "student.dashboard"
