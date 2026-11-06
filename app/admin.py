"""Admin blueprint: dashboard, student management (role protected)."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.utils.decorators import admin_required
from app.utils.validators import as_int
from models import career_model, skill_model, student_model
from models.db import scalar

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def dashboard():
    stats = {
        "students": student_model.count_students(),
        "careers": career_model.count_careers(),
        "skills": skill_model.count_skills(),
        "questions": int(scalar("SELECT COUNT(*) FROM questions WHERE is_active = 1", default=0)),
        "resources": int(scalar("SELECT COUNT(*) FROM learning_resources", default=0)),
        "attempts": int(scalar("SELECT COUNT(*) FROM assessments WHERE status = 'completed'", default=0)),
    }
    recent = student_model.list_students(limit=6)
    return render_template(
        "admin/dashboard.html",
        title="Admin dashboard",
        stats=stats,
        recent_students=recent,
    )


@admin_bp.route("/students")
@admin_required
def students():
    search = (request.args.get("q") or "").strip()[:80]
    page = max(1, as_int(request.args.get("page"), 1) or 1)
    per_page = 20
    offset = (page - 1) * per_page

    rows = student_model.list_students(search=search, limit=per_page, offset=offset)
    total = student_model.count_students()
    pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "admin/students.html",
        title="Students",
        students=rows,
        search=search,
        page=page,
        pages=pages,
        total=total,
    )


@admin_bp.route("/students/<int:student_id>/toggle", methods=["POST"])
@admin_required
def toggle_student(student_id: int):
    row = student_model.get_by_id(student_id)
    if not row or row.get("role") != "student":
        flash("Student not found.", "danger")
        return redirect(url_for("admin.students"))

    new_state = not bool(int(row.get("is_active") or 0))
    student_model.set_active(student_id, new_state)
    flash(
        f"{row['full_name']} is now {'active' if new_state else 'deactivated'}.",
        "success",
    )
    return redirect(url_for("admin.students", q=request.args.get("q", ""), page=request.args.get("page", 1)))
