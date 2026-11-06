"""Skill assessment and AI quiz blueprint."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import current_user
from app.utils.decorators import login_required
from app.utils.validators import as_int
from models import career_model
from services import quiz_service

assessment_bp = Blueprint("assessment", __name__, url_prefix="/student")


def _resolve_career(user: dict, requested: int | None) -> tuple[int | None, list[dict]]:
    careers = career_model.list_careers()
    allowed = {int(c["id"]) for c in careers}
    candidate = requested if requested in allowed else as_int(user.get("career_goal_id"), None)
    if candidate not in allowed:
        candidate = next(iter(allowed), None)
    return candidate, careers


@assessment_bp.route("/assessment")
@login_required
def index():
    user = current_user()
    career_id, careers = _resolve_career(user, as_int(request.args.get("career"), None))

    if not career_id:
        flash("No career paths are configured yet.", "warning")
        return redirect(url_for("student.dashboard"))

    data = quiz_service.overview(user["id"], career_id)

    return render_template(
        "student/assessment.html",
        title="Skill assessment",
        user=user,
        careers=careers,
        selected_id=career_id,
        is_goal=career_id == as_int(user.get("career_goal_id"), None),
        rows=data["rows"],
        career=data["analysis"]["career"],
        totals=data["totals"],
        history=data["history"],
        min_questions=3,
    )


@assessment_bp.route("/assessment/start", methods=["POST"])
@login_required
def start():
    user = current_user()
    skill_id = as_int(request.form.get("skill_id"), None)
    career_id = as_int(request.form.get("career_id"), None)

    if not skill_id:
        flash("Choose a skill to assess.", "warning")
        return redirect(url_for("assessment.index", career=career_id))

    try:
        session = quiz_service.start(user["id"], skill_id)
    except quiz_service.QuizError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("assessment.index", career=career_id))

    if session["generated_note"]:
        flash(session["generated_note"], "info")
    return redirect(url_for("assessment.take", assessment_id=session["assessment_id"]))


@assessment_bp.route("/assessment/<int:assessment_id>")
@login_required
def take(assessment_id: int):
    user = current_user()
    try:
        attempt = quiz_service.load_attempt(assessment_id, user["id"])
    except quiz_service.QuizError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("assessment.index"))

    return render_template(
        "student/quiz.html",
        title=f"{attempt['skill'].get('name', 'Skill')} quiz",
        user=user,
        attempt=attempt,
        questions=attempt["questions"],
    )


@assessment_bp.route("/assessment/<int:assessment_id>/submit", methods=["POST"])
@login_required
def submit(assessment_id: int):
    user = current_user()
    try:
        summary = quiz_service.submit(assessment_id, user["id"], request.form)
    except quiz_service.QuizError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("assessment.index"))

    if summary["note"]:
        flash(summary["note"], "info")
    flash(
        f"Quiz finished: {summary['correct']} of {summary['total']} correct "
        f"({summary['score']:.0f}%).",
        "success",
    )
    return redirect(url_for("assessment.result", assessment_id=assessment_id))


@assessment_bp.route("/assessment/<int:assessment_id>/result")
@login_required
def result(assessment_id: int):
    user = current_user()
    data = quiz_service.result(assessment_id, user["id"])
    if not data:
        flash("That result is not available.", "warning")
        return redirect(url_for("assessment.index"))

    return render_template(
        "student/quiz_result.html",
        title="Quiz result",
        user=user,
        data=data,
    )
