"""Resume repository - SQL only."""

from __future__ import annotations

import json
from typing import Any

from models.db import execute, query_all, query_one, scalar


def insert_record(
    student_id: int,
    career_id: int | None,
    original_name: str,
    stored_name: str,
    file_size: int,
    file_hash: str,
    extracted_text: str,
    detected_skills: list[dict] | None,
    missing_skills: list[str] | None,
    match_score: float | None,
) -> int:
    return execute(
        """
        INSERT INTO resume_records
            (student_id, career_id, original_name, stored_name, file_size,
             file_hash, extracted_text, detected_skills, missing_skills, match_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            student_id,
            career_id,
            original_name,
            stored_name,
            file_size,
            file_hash,
            extracted_text,
            json.dumps(detected_skills) if detected_skills is not None else None,
            json.dumps(missing_skills) if missing_skills is not None else None,
            match_score,
        ),
    )


def list_for_student(student_id: int, limit: int = 10) -> list[dict]:
    return query_all(
        """
        SELECT id, student_id, career_id, original_name, stored_name, file_size,
               file_hash, detected_skills, missing_skills, match_score, uploaded_at
          FROM resume_records
         WHERE student_id = %s
         ORDER BY uploaded_at DESC, id DESC
         LIMIT %s
        """,
        (student_id, limit),
    )


def latest_for_student(student_id: int) -> dict | None:
    return query_one(
        """
        SELECT *
          FROM resume_records
         WHERE student_id = %s
         ORDER BY uploaded_at DESC, id DESC
         LIMIT 1
        """,
        (student_id,),
    )


def get_record(record_id: int, student_id: int) -> dict | None:
    return query_one(
        "SELECT * FROM resume_records WHERE id = %s AND student_id = %s",
        (record_id, student_id),
    )


def count_for_student(student_id: int) -> int:
    return int(
        scalar("SELECT COUNT(*) FROM resume_records WHERE student_id = %s", (student_id,), default=0)
    )


def delete_record(record_id: int, student_id: int) -> int:
    return execute(
        "DELETE FROM resume_records WHERE id = %s AND student_id = %s",
        (record_id, student_id),
    )


def find_by_hash(student_id: int, file_hash: str) -> dict | None:
    return query_one(
        "SELECT id, uploaded_at FROM resume_records "
        "WHERE student_id = %s AND file_hash = %s ORDER BY id DESC LIMIT 1",
        (student_id, file_hash),
    )


def parsed_detected(record: dict | None) -> list[dict]:
    """MySQL returns JSON columns as str on some drivers - normalise both."""
    if not record:
        return []
    raw: Any = record.get("detected_skills")
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


def parsed_missing(record: dict | None) -> list[str]:
    if not record:
        return []
    raw: Any = record.get("missing_skills")
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw]
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return [str(x) for x in value] if isinstance(value, list) else []
