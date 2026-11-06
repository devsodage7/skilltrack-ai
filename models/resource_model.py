"""Learning-resource repository - SQL only."""

from __future__ import annotations

from typing import Iterable

from models.db import query_all, scalar


def list_for_skills(skill_ids: Iterable[int]) -> dict[int, list[dict]]:
    """{skill_id: [resources ordered beginner -> advanced]} for many skills."""
    ids = [int(value) for value in skill_ids]
    if not ids:
        return {}

    placeholders = ", ".join(["%s"] * len(ids))
    rows = query_all(
        f"""
        SELECT id, skill_id, title, provider, url, resource_type, difficulty, est_hours, is_free
          FROM learning_resources
         WHERE skill_id IN ({placeholders})
         ORDER BY FIELD(difficulty, 'beginner', 'intermediate', 'advanced'), est_hours
        """,
        tuple(ids),
    )

    grouped: dict[int, list[dict]] = {}
    for row in rows:
        grouped.setdefault(int(row["skill_id"]), []).append(row)
    return grouped


def list_for_skill(skill_id: int) -> list[dict]:
    return list_for_skills([skill_id]).get(int(skill_id), [])


def count_resources() -> int:
    return int(scalar("SELECT COUNT(*) FROM learning_resources", default=0))
