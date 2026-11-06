"""JSON API blueprint - health probe and chart data."""

from __future__ import annotations

from flask import Blueprint, request

from app.extensions import current_user
from app.utils.responses import fail, ok
from app.utils.validators import as_int
from config import Config
from models import career_model, db
from services import gap_service, performance_service

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health")
def health():
    """Public, read-only status probe used by the setup page and tests."""
    status = db.health_check()
    return ok(
        {
            "database": status,
            "app": "SkillTrack AI",
            "env": Config.FLASK_ENV,
        },
        status=200 if status.get("ok") else 503,
    )


def _career_id(user: dict, raw: str | None) -> int | None:
    careers = career_model.list_careers()
    allowed = {int(c["id"]) for c in careers}
    candidate = as_int(raw, None) or as_int(user.get("career_goal_id"), None)
    return candidate if candidate in allowed else next(iter(allowed), None)


@api_bp.route("/student/performance")
def student_performance():
    """Chart data for the performance page (session protected)."""
    user = current_user()
    if not user:
        return fail("Authentication required.", 401)
    if user.get("role") != "student":
        return fail("Student account required.", 403)

    career_id = _career_id(user, request.args.get("career"))
    if not career_id:
        return fail("No career paths are configured.", 404)

    data = performance_service.overview(user["id"], career_id)
    return ok(
        {
            "charts": performance_service.chart_payload(data),
            "totals": data["totals"],
            "coverage": data["coverage"],
            "career": data["career"],
        },
        career_id=career_id,
    )


@api_bp.route("/student/readiness")
def student_readiness():
    """Compact readiness snapshot used by dashboards."""
    user = current_user()
    if not user:
        return fail("Authentication required.", 401)
    if user.get("role") != "student":
        return fail("Student account required.", 403)

    career_id = _career_id(user, request.args.get("career"))
    if not career_id:
        return fail("No career paths are configured.", 404)

    return ok(gap_service.readiness_snapshot(user["id"], career_id), career_id=career_id)
