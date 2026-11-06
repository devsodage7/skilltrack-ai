"""Resume upload and analysis blueprint."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import current_user
from app.utils.decorators import login_required
from app.utils.validators import as_int
from models import resume_model
from services import resume_service

resume_bp = Blueprint("resume", __name__, url_prefix="/student")


@resume_bp.route("/resume")
@login_required
def index():
    user = current_user()
    latest = resume_service.latest_analysis(user["id"])
    hint = resume_service.profile_hint(user["id"])

    return render_template(
        "student/resume.html",
        title="Resume analyser",
        user=user,
        latest=latest,
        history=resume_service.history(user["id"]),
        hint=hint,
        max_mb=5,
    )


@resume_bp.route("/resume/upload", methods=["POST"])
@login_required
def upload():
    user = current_user()
    career_id = as_int(request.form.get("career_id"), None) or as_int(user.get("career_goal_id"), None)

    try:
        result = resume_service.analyze_upload(
            request.files.get("resume"), user["id"], career_id
        )
    except resume_service.ResumeError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("resume.index"))
    except Exception:  # noqa: BLE001 - keep the page usable
        flash("The resume could not be analysed. Please try another PDF.", "danger")
        return redirect(url_for("resume.index"))

    message = (
        f"Resume analysed: {len(result['detected'])} skill(s) detected, "
        f"{result['skills_updated']} level(s) updated."
    )
    if result["duplicate"]:
        message += " This file was analysed before - the latest result now applies."
    flash(message, "success")
    return redirect(url_for("resume.index"))


@resume_bp.route("/resume/<int:record_id>/delete", methods=["POST"])
@login_required
def delete(record_id: int):
    user = current_user()
    record = resume_model.get_record(record_id, user["id"])
    if not record:
        flash("Resume record not found.", "warning")
        return redirect(url_for("resume.index"))

    stored = record.get("stored_name")
    resume_model.delete_record(record_id, user["id"])
    if stored:
        resume_service.delete_file(stored)
    flash("Resume record removed. Your existing skill levels were kept.", "info")
    return redirect(url_for("resume.index"))
