"""Student repository - SQL only, no business rules."""

from __future__ import annotations

from typing import Any

from models.db import execute, insert, query_all, query_one, scalar

PUBLIC_COLUMNS = """
    s.id, s.full_name, s.email, s.role, s.phone, s.education, s.college,
    s.branch, s.year_of_study, s.career_goal_id, s.interests, s.weekly_hours,
    s.is_active, s.created_at, s.updated_at
"""


def get_by_id(student_id: int) -> dict | None:
    return query_one(
        f"SELECT {PUBLIC_COLUMNS} FROM students s WHERE s.id = %s",
        (student_id,),
    )


def get_by_email(email: str) -> dict | None:
    """Includes password_hash - used only by the login path."""
    return query_one(
        "SELECT id, full_name, email, password_hash, role, is_active "
        "FROM students WHERE email = %s",
        (email,),
    )


def email_exists(email: str, exclude_id: int | None = None) -> bool:
    if exclude_id:
        return bool(
            scalar(
                "SELECT COUNT(*) FROM students WHERE email = %s AND id <> %s",
                (email, exclude_id),
                default=0,
            )
        )
    return bool(scalar("SELECT COUNT(*) FROM students WHERE email = %s", (email,), default=0))


def create(full_name: str, email: str, password_hash: str, role: str = "student") -> int:
    return insert(
        "INSERT INTO students (full_name, email, password_hash, role) "
        "VALUES (%s, %s, %s, %s)",
        (full_name, email, password_hash, role),
    )


def update_profile(student_id: int, data: dict[str, Any]) -> int:
    return execute(
        """
        UPDATE students
           SET full_name     = %s,
               phone         = %s,
               education     = %s,
               college       = %s,
               branch        = %s,
               year_of_study = %s,
               career_goal_id= %s,
               interests     = %s,
               weekly_hours  = %s
         WHERE id = %s
        """,
        (
            data["full_name"],
            data.get("phone"),
            data.get("education"),
            data.get("college"),
            data.get("branch"),
            data.get("year_of_study"),
            data.get("career_goal_id"),
            data.get("interests"),
            data.get("weekly_hours", 10),
            student_id,
        ),
    )


def set_active(student_id: int, active: bool) -> int:
    return execute(
        "UPDATE students SET is_active = %s WHERE id = %s AND role = 'student'",
        (1 if active else 0, student_id),
    )


def set_career_goal(student_id: int, career_id: int | None) -> int:
    """Targeted update so choosing a career never rewrites the whole profile."""
    return execute(
        "UPDATE students SET career_goal_id = %s WHERE id = %s",
        (career_id, student_id),
    )


def list_students(search: str = "", limit: int = 100, offset: int = 0) -> list[dict]:
    if search:
        like = f"%{search}%"
        return query_all(
            f"""
            SELECT {PUBLIC_COLUMNS},
                   c.name AS career_goal_name
              FROM students s
              LEFT JOIN careers c ON c.id = s.career_goal_id
             WHERE s.role = 'student'
               AND (s.full_name LIKE %s OR s.email LIKE %s OR s.college LIKE %s)
             ORDER BY s.created_at DESC
             LIMIT %s OFFSET %s
            """,
            (like, like, like, limit, offset),
        )
    return query_all(
        f"""
        SELECT {PUBLIC_COLUMNS},
               c.name AS career_goal_name
          FROM students s
          LEFT JOIN careers c ON c.id = s.career_goal_id
         WHERE s.role = 'student'
         ORDER BY s.created_at DESC
         LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )


def count_students() -> int:
    return int(scalar("SELECT COUNT(*) FROM students WHERE role = 'student'", default=0))


def profile_completion(student: dict | None) -> int:
    """Percentage of profile fields filled. Used by the dashboard prompt."""
    if not student:
        return 0
    fields = [
        "full_name",
        "education",
        "college",
        "branch",
        "year_of_study",
        "career_goal_id",
        "interests",
        "weekly_hours",
    ]
    filled = sum(1 for f in fields if student.get(f) not in (None, "", 0))
    return round(filled / len(fields) * 100)
