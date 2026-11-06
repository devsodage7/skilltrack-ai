"""Question-bank repository - SQL only."""

from __future__ import annotations

import json
from typing import Any, Sequence

from models.db import execute, insert, query_all, query_one, scalar

DIFFICULTY_ORDER = ("beginner", "intermediate", "advanced")


def parse_options(row: dict | None) -> list[str]:
    """MySQL JSON columns arrive as str (or list on some drivers)."""
    if not row:
        return []
    raw: Any = row.get("options")
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(value) for value in raw]
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def upgrade(row: dict | None) -> dict | None:
    """Attach parsed options and a stable option list to a question row."""
    if not row:
        return None
    row = dict(row)
    row["options_list"] = parse_options(row)
    row["is_mcq"] = str(row.get("question_type")) == "mcq" and len(row["options_list"]) >= 2
    return row


def get(question_id: int) -> dict | None:
    return upgrade(
        query_one("SELECT * FROM questions WHERE id = %s AND is_active = 1", (question_id,))
    )


def list_for_skill(skill_id: int, active_only: bool = True) -> list[dict]:
    """Ordered by difficulty then id, so selection is deterministic."""
    sql = "SELECT * FROM questions WHERE skill_id = %s"
    if active_only:
        sql += " AND is_active = 1"
    sql += " ORDER BY FIELD(difficulty, 'beginner', 'intermediate', 'advanced'), id"
    return [upgrade(row) for row in query_all(sql, (skill_id,))]


def list_by_ids(ids: Sequence[int]) -> list[dict]:
    clean = [int(value) for value in ids]
    if not clean:
        return []
    placeholders = ", ".join(["%s"] * len(clean))
    rows = query_all(
        f"SELECT * FROM questions WHERE id IN ({placeholders}) AND is_active = 1",
        tuple(clean),
    )
    by_id = {int(row["id"]): upgrade(row) for row in rows}
    return [by_id[value] for value in clean if value in by_id]


def count_for_skill(skill_id: int) -> int:
    return int(
        scalar(
            "SELECT COUNT(*) FROM questions WHERE skill_id = %s AND is_active = 1",
            (skill_id,),
            default=0,
        )
    )


def count_map() -> dict[int, int]:
    """{skill_id: active question count} for the whole catalogue."""
    rows = query_all(
        "SELECT skill_id, COUNT(*) AS n FROM questions WHERE is_active = 1 GROUP BY skill_id"
    )
    return {int(row["skill_id"]): int(row["n"]) for row in rows}


def existing_texts(skill_id: int) -> set[str]:
    """Question texts already stored for a skill (dedupe key for generation)."""
    rows = query_all("SELECT question_text FROM questions WHERE skill_id = %s", (skill_id,))
    return {str(row["question_text"]).strip().lower() for row in rows}


def insert_question(
    skill_id: int,
    question_type: str,
    difficulty: str,
    question_text: str,
    options: Sequence[str] | None,
    correct_option: int | None,
    correct_answer: str | None,
    explanation: str,
    source: str = "template",
    created_by: int | None = None,
) -> int:
    if question_type not in {"mcq", "output", "coding", "scenario"}:
        question_type = "mcq"
    if difficulty not in DIFFICULTY_ORDER:
        difficulty = "beginner"
    if source not in {"manual", "template", "ollama"}:
        source = "template"

    return insert(
        """
        INSERT INTO questions
            (skill_id, question_type, difficulty, question_text, code_snippet,
             options, correct_option, correct_answer, explanation, source,
             is_validated, is_active, created_by)
        VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, 0, 1, %s)
        """,
        (
            skill_id,
            question_type,
            difficulty,
            question_text,
            json.dumps(list(options)) if options is not None else None,
            correct_option,
            correct_answer,
            explanation,
            source,
            created_by,
        ),
    )


def deactivate(question_id: int) -> int:
    """Soft delete so historical quiz_results keep their foreign key."""
    return execute("UPDATE questions SET is_active = 0 WHERE id = %s", (question_id,))
