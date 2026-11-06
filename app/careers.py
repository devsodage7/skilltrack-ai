"""Career catalogue, goal selection and weighted gap analysis."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.extensions import current_user
from app.utils.decorators import login_required
from app.utils.validators import as_int
from ml import career_matcher
from models import career_model, student_model
from services import career_service, gap_service

careers_bp = Blueprint("careers", __name__, url_prefix="/student")


@careers_bp.route("/careers")
@login_required
def catalog():
    """All 8 careers ranked by the student's current readiness."""
    user = current_user()
    analyses = gap_service.analyze_all(user["id"])
    goal_id = as_int(user.get("career_goal_id"), None)

    return render_template(
        "student/careers.html",
        title="Career paths",
        user=user,
        analyses=analyses,
        goal_id=goal_id,
        best=analyses[0] if analyses else None,
    )


@careers_bp.route("/careers/<int:career_id>/select", methods=["POST"])
@login_required
def select(career_id: int):
    user = current_user()
    career = career_model.get_career(career_id)
    if not career:
        abort(404)

    student_model.set_career_goal(user["id"], career_id)
    flash(f"{career['name']} is now your target career.", "success")
    return redirect(url_for("careers.gap", career=career_id))


@careers_bp.route("/gap")
@login_required
def gap():
    """Weighted gap table + readiness score for one career."""
    user = current_user()
    careers = career_model.list_careers()
    allowed = {int(c["id"]): c for c in careers}
    if not allowed:
        flash("No career paths are configured yet.", "warning")
        return redirect(url_for("student.dashboard"))

    requested = as_int(request.args.get("career"), None)
    career_id = requested if requested in allowed else as_int(user.get("career_goal_id"), None)
    if career_id not in allowed:
        career_id = next(iter(allowed))

    analysis = gap_service.analyze(user["id"], career_id)
    projection = gap_service.projected_readiness(analysis, top_n=3)

    return render_template(
        "student/gap.html",
        title="Skill gap analysis",
        user=user,
        careers=careers,
        selected_id=career_id,
        analysis=analysis,
        projection=projection,
        is_goal=career_id == as_int(user.get("career_goal_id"), None),
    )


@careers_bp.route("/recommendations")
@login_required
def recommendations():
    """Hybrid ranking: weighted readiness + interest similarity."""
    user = current_user()
    ranked = career_service.recommend(user["id"])

    return render_template(
        "student/recommendations.html",
        title="Career recommendations",
        user=user,
        ranked=ranked,
        goal_id=as_int(user.get("career_goal_id"), None),
        explanation=career_matcher.explain_blend(),
        disclaimer=career_matcher.Config.RECOMMENDATION_DISCLAIMER,
    )
