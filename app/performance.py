"""Performance analytics blueprint (charts + tables)."""

from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, url_for

from app.extensions import current_user
from app.utils.decorators import login_required
from app.utils.validators import as_int
from models import career_model
from services import performance_service

performance_bp = Blueprint("performance", __name__, url_prefix="/student")


def resolve_career(user: dict, requested: int | None) -> tuple[int | None, list[dict]]:
    careers = career_model.list_careers()
    allowed = {int(c["id"]) for c in careers}
    candidate = requested if requested in allowed else as_int(user.get("career_goal_id"), None)
    if candidate not in allowed:
        candidate = next(iter(allowed), None)
    return candidate, careers


@performance_bp.route("/performance")
@login_required
def index():
    user = current_user()
    career_id, careers = resolve_career(user, as_int(request.args.get("career"), None))
    if not career_id:
        return redirect(url_for("student.dashboard"))

    data = performance_service.overview(user["id"], career_id)

    return render_template(
        "student/performance.html",
        title="Performance analysis",
        user=user,
        careers=careers,
        selected_id=career_id,
        is_goal=career_id == as_int(user.get("career_goal_id"), None),
        data=data,
        charts=performance_service.chart_payload(data),
    )
