"""Skill repository - SQL only."""

from __future__ import annotations

from models.db import execute, query_all, query_one, scalar

LEVEL_SOURCES = ("self", "resume", "quiz")


def list_skills(category: str | None = None) -> list[dict]:
    if category:
        return query_all(
            "SELECT id, name, category, description FROM skills "
            "WHERE category = %s ORDER BY name",
            (category,),
        )
    return query_all(
        "SELECT id, name, category, description FROM skills ORDER BY category, name"
    )


def get_skill(skill_id: int) -> dict | None:
    return query_one(
        "SELECT id, name, category, description FROM skills WHERE id = %s",
        (skill_id,),
    )


def count_skills() -> int:
    return int(scalar("SELECT COUNT(*) FROM skills", default=0))


def get_student_skill(student_id: int, skill_id: int) -> dict | None:
    return query_one(
        "SELECT * FROM student_skills WHERE student_id = %s AND skill_id = %s",
        (student_id, skill_id),
    )


def list_student_skills(student_id: int) -> list[dict]:
    """All rows the student has evidence for, with skill metadata."""
    return query_all(
        """
        SELECT ss.*, s.name AS skill_name, s.category AS skill_category
          FROM student_skills ss
          JOIN skills s ON s.id = ss.skill_id
         WHERE ss.student_id = %s
         ORDER BY ss.current_level DESC, s.name
        """,
        (student_id,),
    )


def list_student_skill_map(student_id: int) -> dict[int, dict]:
    """{skill_id: row} for quick lookups in templates and services."""
    return {int(row["skill_id"]): row for row in list_student_skills(student_id)}


def count_detected_skills(student_id: int, min_level: float = 1.0) -> int:
    return int(
        scalar(
            "SELECT COUNT(*) FROM student_skills "
            "WHERE student_id = %s AND current_level >= %s",
            (student_id, min_level),
            default=0,
        )
    )


def upsert_student_skill(
    student_id: int,
    skill_id: int,
    self_level: float | None = None,
    resume_level: float | None = None,
    quiz_level: float | None = None,
    current_level: float = 0.0,
    last_source: str = "self",
    evidence_count: int | None = None,
) -> int:
    """
    Insert or update one skill row. Any level passed as None is left
    untouched on update, so a resume upload does not erase a self rating.
    """
    existing = get_student_skill(student_id, skill_id)

    if existing is None:
        return _insert_row(
            student_id,
            skill_id,
            self_level,
            resume_level,
            quiz_level,
            current_level,
            last_source,
            evidence_count if evidence_count is not None else 1,
        )

    merged = {
        "self_level": self_level if self_level is not None else existing["self_level"],
        "resume_level": resume_level if resume_level is not None else existing["resume_level"],
        "quiz_level": quiz_level if quiz_level is not None else existing["quiz_level"],
    }
    count = evidence_count
    if count is None:
        count = int(existing.get("evidence_count") or 0) + 1
    return execute(
        """
        UPDATE student_skills
           SET self_level     = %s,
               resume_level   = %s,
               quiz_level     = %s,
               current_level  = %s,
               evidence_count = %s,
               last_source    = %s
         WHERE student_id = %s AND skill_id = %s
        """,
        (
            merged["self_level"],
            merged["resume_level"],
            merged["quiz_level"],
            current_level,
            count,
            last_source,
            student_id,
            skill_id,
        ),
    )


def _insert_row(student_id, skill_id, self_level, resume_level, quiz_level,
                current_level, last_source, evidence_count) -> int:
    return execute(
        """
        INSERT INTO student_skills
            (student_id, skill_id, self_level, resume_level, quiz_level,
             current_level, evidence_count, last_source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            student_id,
            skill_id,
            self_level,
            resume_level,
            quiz_level,
            current_level,
            evidence_count,
            last_source,
        ),
    )


def delete_student_skill(student_id: int, skill_id: int) -> int:
    return execute(
        "DELETE FROM student_skills WHERE student_id = %s AND skill_id = %s",
        (student_id, skill_id),
    )


def skills_for_career(career_id: int) -> list[dict]:
    return query_all(
        """
        SELECT cs.skill_id, cs.required_level, cs.weight, cs.prerequisite_skill_id,
               s.name AS skill_name, s.category
          FROM career_skills cs
          JOIN skills s ON s.id = cs.skill_id
         WHERE cs.career_id = %s
         ORDER BY cs.weight DESC, s.name
        """,
        (career_id,),
    )
