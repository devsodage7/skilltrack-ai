"""Student blueprint: dashboard and profile (skills self-assessment)."""

from __future__ import annotations

from collections import OrderedDict

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import current_user
from app.utils.decorators import login_required
from app.utils.validators import as_level, level_label, validate_profile
from models import assessment_model, career_model, resume_model, skill_model, student_model
from services import career_service, gap_service, skill_service

student_bp = Blueprint("student", __name__, url_prefix="/student")

CATEGORY_ORDER = [
    ("programming", "Programming languages"),
    ("framework", "Frameworks and web"),
    ("database", "Databases"),
    ("tool", "Tools and platforms"),
    ("concept", "Concepts and theory"),
    ("soft", "Soft skills"),
]


def _group_skills(skills: list[dict]) -> "OrderedDict[str, list[dict]]":
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    by_category: dict[str, list[dict]] = {}
    for skill in skills:
        by_category.setdefault(skill["category"], []).append(skill)
    for key, label in CATEGORY_ORDER:
        if by_category.get(key):
            grouped[label] = by_category[key]
    # any unexpected category still gets rendered
    for key, items in by_category.items():
        if key not in dict(CATEGORY_ORDER):
            grouped[key.title()] = items
    return grouped


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------
@student_bp.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    skills = skill_model.list_student_skills(user["id"])
    careers = career_model.list_careers()

    strong = [s for s in skills if float(s["current_level"]) >= 4]
    developing = [s for s in skills if 2 <= float(s["current_level"]) < 4]
    weak = [s for s in skills if 0 < float(s["current_level"]) < 2]

    goal = None
    requirements_by_skill: dict[int, dict] = {}
    snapshot = None
    if user.get("career_goal_id"):
        goal = career_model.get_career(int(user["career_goal_id"]))
        if goal:
            requirements_by_skill = {
                int(row["skill_id"]): row
                for row in career_model.career_requirements(int(goal["id"]))
            }
            snapshot = gap_service.readiness_snapshot(user["id"], int(goal["id"]))

    recommendation = None
    try:
        best = career_service.best_matches(user["id"], limit=1)
        recommendation = best[0] if best else None
    except Exception:  # noqa: BLE001 - never break the dashboard
        recommendation = None

    resume_count = resume_model.count_for_student(user["id"])
    recent_attempts = assessment_model.list_for_student(user["id"], limit=3)

    return render_template(
        "student/dashboard.html",
        title="Dashboard",
        user=user,
        skills=skills,
        strong=strong,
        developing=developing,
        weak=weak,
        careers=careers,
        goal=goal,
        requirements_by_skill=requirements_by_skill,
        snapshot=snapshot,
        recommendation=recommendation,
        resume_count=resume_count,
        recent_attempts=recent_attempts,
        completion=student_model.profile_completion(user),
        level_label=level_label,
    )


# ---------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------
@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    careers = career_model.list_careers()
    skills = skill_model.list_skills()
    skill_map = skill_model.list_student_skill_map(user["id"])

    errors: dict = {}

    if request.method == "POST":
        data, errors = validate_profile(
            request.form, valid_career_ids=[c["id"] for c in careers]
        )

        if not errors:
            try:
                student_model.update_profile(user["id"], data)
                changed = _save_skill_levels(user["id"], skills, skill_map)
            except Exception:  # noqa: BLE001
                flash("Could not save your profile. Please try again.", "danger")
                errors["form"] = "A database error occurred while saving."
            else:
                message = "Profile saved."
                if changed:
                    message = f"Profile saved. {changed} skill rating(s) updated."
                flash(message, "success")
                return redirect(url_for("student.profile"))
        else:
            flash("Please fix the highlighted fields.", "danger")

        # Keep the submitted values visible after a validation error
        form_view = dict(user)
        form_view.update(data)

    else:
        form_view = user

    status = 400 if (request.method == "POST" and errors) else 200
    return (
        render_template(
            "student/profile.html",
            title="My profile",
            user=user,
            form=form_view,
            errors=errors,
            careers=careers,
            skill_groups=_group_skills(skills),
            skill_map=skill_map,
            class_years=[1, 2, 3, 4, 5],
            completion=student_model.profile_completion(user),
            level_label=level_label,
        ),
        status,
    )


def _save_skill_levels(student_id: int, skills: list[dict], skill_map: dict) -> int:
    """Persist only the skill sliders that actually changed."""
    changed = 0
    for skill in skills:
        field = f"skill_{skill['id']}"
        if field not in request.form:
            continue

        new_level = as_level(request.form.get(field))
        existing = skill_map.get(int(skill["id"])) or {}
        old_level = existing.get("self_level")

        if old_level is not None and abs(float(old_level) - new_level) < 1e-9:
            continue
        if old_level is None and new_level <= 0:
            continue

        skill_service.set_self_level(student_id, int(skill["id"]), new_level)
        changed += 1

    return changed
