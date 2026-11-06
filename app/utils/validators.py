"""
Form validation.

Every validator returns (clean_data, errors) where errors is a dict of
{field_name: message} ready to be rendered next to the input.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from app.utils.security import password_errors

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

MAX_NAME = 120
MAX_TEXT = 160
MAX_INTERESTS = 255
MIN_AGE_YEAR = 1
MAX_YEAR = 5
MIN_HOURS = 1
MAX_HOURS = 60


def clean_text(value: Any, max_length: int = MAX_TEXT) -> str:
    """Trim, collapse whitespace and cut to a safe length."""
    if value is None:
        return ""
    text = " ".join(str(value).split())
    return text[:max_length]


def as_int(value: Any, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def as_level(value: Any) -> float:
    """Skill level input -> 0.0-5.0 (invalid becomes 0.0)."""
    if value is None or value == "":
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number != number:  # NaN
        return 0.0
    return round(max(0.0, min(5.0, number)), 1)


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


# ---------------------------------------------------------------------
# Registration / login
# ---------------------------------------------------------------------
def validate_registration(form: Mapping[str, Any]) -> tuple[dict, dict]:
    data = {
        "full_name": clean_text(form.get("full_name"), MAX_NAME),
        "email": clean_text(form.get("email"), MAX_TEXT).lower(),
        "password": str(form.get("password") or ""),
        "confirm_password": str(form.get("confirm_password") or ""),
    }
    errors: dict[str, str] = {}

    if len(data["full_name"]) < 3:
        errors["full_name"] = "Enter your full name (at least 3 characters)."
    elif not re.fullmatch(r"[A-Za-z .'\-]+", data["full_name"]):
        errors["full_name"] = "Use letters, spaces, dots, hyphens or apostrophes only."

    if not is_valid_email(data["email"]):
        errors["email"] = "Enter a valid email address, for example name@college.edu."

    policy = password_errors(data["password"])
    if policy:
        errors["password"] = " ".join(policy)

    if data["password"] != data["confirm_password"]:
        errors["confirm_password"] = "Passwords do not match."

    return data, errors


def validate_login(form: Mapping[str, Any]) -> tuple[dict, dict]:
    data = {
        "email": clean_text(form.get("email"), MAX_TEXT).lower(),
        "password": str(form.get("password") or ""),
    }
    errors: dict[str, str] = {}
    if not is_valid_email(data["email"]):
        errors["email"] = "Enter the email you registered with."
    if not data["password"]:
        errors["password"] = "Enter your password."
    return data, errors


# ---------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------
def validate_profile(
    form: Mapping[str, Any],
    valid_career_ids: Iterable[int] = (),
) -> tuple[dict, dict]:
    """
    Validate the profile form.

    career_goal_id must be one of valid_career_ids (or empty). Passing the
    allowed ids in prevents a tampered form from pointing at a deleted career.
    """
    data = {
        "full_name": clean_text(form.get("full_name"), MAX_NAME),
        "phone": clean_text(form.get("phone"), 20),
        "education": clean_text(form.get("education"), MAX_TEXT),
        "college": clean_text(form.get("college"), MAX_TEXT),
        "branch": clean_text(form.get("branch"), MAX_TEXT),
        "year_of_study": as_int(form.get("year_of_study"), None),
        "career_goal_id": as_int(form.get("career_goal_id"), None),
        "interests": clean_text(form.get("interests"), MAX_INTERESTS),
        "weekly_hours": as_int(form.get("weekly_hours"), 10),
    }
    errors: dict[str, str] = {}

    if len(data["full_name"]) < 3:
        errors["full_name"] = "Name is required (at least 3 characters)."

    if data["phone"] and not re.fullmatch(r"[0-9+\-() ]{7,20}", data["phone"]):
        errors["phone"] = "Enter a valid phone number or leave it blank."

    if data["year_of_study"] is not None and not (
        MIN_AGE_YEAR <= data["year_of_study"] <= MAX_YEAR
    ):
        errors["year_of_study"] = f"Year must be between {MIN_AGE_YEAR} and {MAX_YEAR}."

    if data["weekly_hours"] is None or not (MIN_HOURS <= data["weekly_hours"] <= MAX_HOURS):
        errors["weekly_hours"] = f"Study hours must be between {MIN_HOURS} and {MAX_HOURS} per week."

    allowed = {int(x) for x in valid_career_ids if x is not None}
    if data["career_goal_id"] is not None:
        if data["career_goal_id"] not in allowed:
            errors["career_goal_id"] = "Choose a career from the list."
            data["career_goal_id"] = None

    if len(data["interests"]) > MAX_INTERESTS:
        errors["interests"] = f"Keep interests under {MAX_INTERESTS} characters."

    return data, errors


# ---------------------------------------------------------------------
# Small helpers used by templates
# ---------------------------------------------------------------------
def level_label(level: float | None) -> str:
    """0-5 level -> short human label."""
    value = as_level(level)
    if value <= 0:
        return "No experience"
    if value < 1.5:
        return "Beginner"
    if value < 2.5:
        return "Basic"
    if value < 3.5:
        return "Working knowledge"
    if value < 4.5:
        return "Strong"
    return "Expert"
