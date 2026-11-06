"""Authentication blueprint: register, login, logout."""

from __future__ import annotations

import time

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.extensions import current_user, login_user, logout_user
from app.utils.decorators import guest_only, login_required, safe_next_url
from app.utils.security import hash_password, verify_password
from app.utils.validators import validate_login, validate_registration
from models import student_model

auth_bp = Blueprint("auth", __name__)

MAX_ATTEMPTS = 10
LOCKOUT_SECONDS = 60


def _too_many_attempts() -> bool:
    attempts = int(session.get("login_attempts", 0))
    first_ts = float(session.get("login_first_ts", 0) or 0)
    if attempts < MAX_ATTEMPTS:
        return False
    if time.time() - first_ts > LOCKOUT_SECONDS:
        session.pop("login_attempts", None)
        session.pop("login_first_ts", None)
        return False
    return True


def _record_failure() -> None:
    attempts = int(session.get("login_attempts", 0)) + 1
    session["login_attempts"] = attempts
    if attempts == 1:
        session["login_first_ts"] = time.time()


def _clear_failures() -> None:
    session.pop("login_attempts", None)
    session.pop("login_first_ts", None)


# ---------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
@guest_only
def register():
    form_data: dict = {}
    errors: dict = {}

    if request.method == "POST":
        data, errors = validate_registration(request.form)
        form_data = {"full_name": data["full_name"], "email": data["email"]}

        if not errors and student_model.email_exists(data["email"]):
            errors["email"] = "An account with this email already exists. Try logging in."

        if not errors:
            try:
                student_id = student_model.create(
                    full_name=data["full_name"],
                    email=data["email"],
                    password_hash=hash_password(data["password"]),
                    role="student",
                )
            except Exception:  # noqa: BLE001 - unique race or DB hiccup
                current_app.logger.exception("Registration failed")
                errors["form"] = "We could not create the account. Please try again."
            else:
                user = student_model.get_by_id(student_id)
                login_user(user or {"id": student_id, "role": "student"})
                flash(
                    "Welcome to SkillTrack AI. Complete your profile to get your first readiness score.",
                    "success",
                )
                return redirect(url_for("student.profile"))

    status = 400 if errors else 200
    return (
        render_template(
            "auth/register.html",
            errors=errors,
            form=form_data,
            title="Create account",
        ),
        status,
    )


# ---------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
@guest_only
def login():
    errors: dict = {}
    email_value = ""

    if request.method == "POST":
        if _too_many_attempts():
            errors["form"] = (
                f"Too many failed attempts. Wait {LOCKOUT_SECONDS} seconds and try again."
            )
        else:
            data, errors = validate_login(request.form)
            email_value = data.get("email", "")

            if not errors:
                row = student_model.get_by_email(data["email"])
                if not row or not verify_password(row.get("password_hash"), data["password"]):
                    _record_failure()
                    # Deliberately identical message for unknown email and wrong password
                    errors["form"] = "Email or password is incorrect."
                elif int(row.get("is_active") or 0) != 1:
                    errors["form"] = (
                        "This account is deactivated. Contact the administrator."
                    )
                else:
                    _clear_failures()
                    login_user(row)
                    flash(f"Welcome back, {row['full_name'].split()[0]}.", "success")
                    if row.get("role") == "admin":
                        return redirect(url_for("admin.dashboard"))
                    return redirect(safe_next_url(request.args.get("next"), "student.dashboard"))

    status = 400 if errors else 200
    return (
        render_template(
            "auth/login.html", errors=errors, email=email_value, title="Login"
        ),
        status,
    )


# ---------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/", methods=["GET"])
def index():
    """Landing page: send signed-in users to their dashboard."""
    user = current_user()
    if user:
        if user.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))
    return redirect(url_for("auth.login"))
