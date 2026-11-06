"""Learning-progress repository - SQL only (the generated roadmap lives here)."""

from __future__ import annotations

import datetime as _dt
from typing import Iterable, Mapping

from models.db import execute, query_all, query_one, scalar


def list_for(student_id: int, career_id: int) -> list[dict]:
    return query_all(
        """
        SELECT lp.id, lp.student_id, lp.career_id, lp.skill_id, lp.resource_id,
               lp.topic_title, lp.planned_hours, lp.week_number, lp.status, lp.completed_at,
               s.name AS skill_name, s.category AS skill_category,
               lr.title AS resource_title, lr.provider AS resource_provider,
               lr.url AS resource_url, lr.resource_type, lr.est_hours
          FROM learning_progress lp
          JOIN skills s ON s.id = lp.skill_id
          LEFT JOIN learning_resources lr ON lr.id = lp.resource_id
         WHERE lp.student_id = %s AND lp.career_id = %s
         ORDER BY lp.week_number, s.name
        """,
        (student_id, career_id),
    )


def get(progress_id: int, student_id: int, career_id: int) -> dict | None:
    return query_one(
        "SELECT * FROM learning_progress "
        "WHERE id = %s AND student_id = %s AND career_id = %s",
        (progress_id, student_id, career_id),
    )


def clear(student_id: int, career_id: int) -> int:
    return execute(
        "DELETE FROM learning_progress WHERE student_id = %s AND career_id = %s",
        (student_id, career_id),
    )


def insert_many(student_id: int, career_id: int, items: Iterable[Mapping]) -> int:
    """
    Insert roadmap rows one by one (small N, clearer errors than executemany).

    `items` keys: skill_id, resource_id, topic_title, week_number, status,
    planned_hours.
    """
    inserted = 0
    for item in items:
        execute(
            """
            INSERT INTO learning_progress
                (student_id, career_id, skill_id, resource_id, topic_title,
                 planned_hours, week_number, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                student_id,
                career_id,
                int(item["skill_id"]),
                item.get("resource_id"),
                str(item["topic_title"])[:200],
                float(item.get("planned_hours") or 6.0),
                int(item["week_number"]),
                item.get("status", "pending"),
            ),
        )
        inserted += 1
    return inserted


def set_status(student_id: int, career_id: int, progress_id: int, status: str) -> int:
    completed_at = _dt.datetime.now() if status == "completed" else None
    return execute(
        """
        UPDATE learning_progress
           SET status = %s, completed_at = %s
         WHERE id = %s AND student_id = %s AND career_id = %s
        """,
        (status, completed_at, progress_id, student_id, career_id),
    )


def summary(student_id: int, career_id: int) -> dict:
    rows = query_all(
        """
        SELECT status, COUNT(*) AS n
          FROM learning_progress
         WHERE student_id = %s AND career_id = %s
         GROUP BY status
        """,
        (student_id, career_id),
    )
    counts = {"pending": 0, "in_progress": 0, "completed": 0}
    for row in rows:
        counts[str(row["status"])] = int(row["n"])
    total = sum(counts.values())
    return {
        "counts": counts,
        "total": total,
        "completed": counts["completed"],
        "pct": round(counts["completed"] / total * 100, 1) if total else 0.0,
    }


def exists(student_id: int, career_id: int) -> bool:
    return bool(
        scalar(
            "SELECT COUNT(*) FROM learning_progress WHERE student_id = %s AND career_id = %s",
            (student_id, career_id),
            default=0,
        )
    )
