"""Roadmap blueprint: generate, view and update a personalised study plan."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import current_user
from app.utils.decorators import login_required
from app.utils.validators import as_int
from models import career_model
from services import gap_service, roadmap_service

roadmap_bp = Blueprint("roadmap", __name__, url_prefix="/student")


def _resolve_career(user: dict, requested: int | None) -> tuple[int | None, list[dict]]:
    careers = career_model.list_careers()
    allowed = {int(c["id"]) for c in careers}
    candidate = requested if requested in allowed else as_int(user.get("career_goal_id"), None)
    if candidate not in allowed:
        candidate = next(iter(allowed), None)
    return candidate, careers


@roadmap_bp.route("/roadmap")
@login_required
def index():
    user = current_user()
    career_id, careers = _resolve_career(user, as_int(request.args.get("career"), None))

    if not career_id:
        flash("No career paths are configured yet.", "warning")
        return redirect(url_for("student.dashboard"))

    plan = roadmap_service.ensure_plan(user["id"], career_id)
    analysis = gap_service.analyze(user["id"], career_id)

    return render_template(
        "student/roadmap.html",
        title="Learning roadmap",
        user=user,
        careers=careers,
        selected_id=career_id,
        plan=plan,
        analysis=analysis,
        is_goal=career_id == as_int(user.get("career_goal_id"), None),
        explanation=roadmap_service.explain_order(),
    )


@roadmap_bp.route("/roadmap/regenerate", methods=["POST"])
@login_required
def regenerate():
    user = current_user()
    career_id, _ = _resolve_career(user, as_int(request.form.get("career_id"), None))
    if not career_id:
        flash("Choose a career first.", "warning")
        return redirect(url_for("careers.catalog"))

    plan = roadmap_service.generate(user["id"], career_id, force=True)
    if plan is None:
        flash("You already meet every requirement for this career - nothing to schedule.", "info")
    else:
        flash("Roadmap regenerated. Completed topics were kept.", "success")
    return redirect(url_for("roadmap.index", career=career_id))


@roadmap_bp.route("/roadmap/<int:progress_id>/status", methods=["POST"])
@login_required
def update_status(progress_id: int):
    user = current_user()
    career_id, _ = _resolve_career(user, as_int(request.form.get("career_id"), None))
    status = (request.form.get("status") or "").strip()

    if not career_id:
        flash("Career not found.", "warning")
        return redirect(url_for("student.dashboard"))

    if roadmap_service.set_topic_status(user["id"], career_id, progress_id, status):
        flash("Topic updated.", "success")
    else:
        flash("That topic could not be updated.", "warning")
    return redirect(url_for("roadmap.index", career=career_id))
