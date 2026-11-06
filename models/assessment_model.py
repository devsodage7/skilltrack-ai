"""Assessment / quiz repository - SQL only."""

from __future__ import annotations

import datetime as _dt

from models.db import execute, insert, query_all, query_one, scalar


# ---------------------------------------------------------------------
# Assessment headers
# ---------------------------------------------------------------------
def create(
    student_id: int,
    skill_id: int | None,
    assessment_type: str,
    total_questions: int,
) -> int:
    if assessment_type not in {"mcq", "output", "coding", "scenario", "mixed"}:
        assessment_type = "mcq"
    return insert(
        """
        INSERT INTO assessments
            (student_id, skill_id, assessment_type, total_questions, status)
        VALUES (%s, %s, %s, %s, 'in_progress')
        """,
        (student_id, skill_id, assessment_type, max(1, int(total_questions))),
    )


def get(assessment_id: int, student_id: int) -> dict | None:
    return query_one(
        "SELECT * FROM assessments WHERE id = %s AND student_id = %s",
        (assessment_id, student_id),
    )


def list_in_progress(student_id: int) -> list[dict]:
    return query_all(
        "SELECT * FROM assessments WHERE student_id = %s AND status = 'in_progress' "
        "ORDER BY started_at DESC, id DESC",
        (student_id,),
    )


def abandon(assessment_id: int, student_id: int) -> int:
    return execute(
        "UPDATE assessments SET status = 'abandoned', completed_at = %s "
        "WHERE id = %s AND student_id = %s AND status = 'in_progress'",
        (_dt.datetime.now(), assessment_id, student_id),
    )


def abandon_all_in_progress(student_id: int, except_id: int | None = None) -> int:
    sql = "UPDATE assessments SET status = 'abandoned', completed_at = %s " \
          "WHERE student_id = %s AND status = 'in_progress'"
    params: list = [_dt.datetime.now(), student_id]
    if except_id:
        sql += " AND id <> %s"
        params.append(except_id)
    return execute(sql, tuple(params))


def complete(
    assessment_id: int,
    correct_answers: int,
    score_pct: float,
    level_awarded: float | None,
    duration_sec: int | None,
) -> int:
    return execute(
        """
        UPDATE assessments
           SET correct_answers = %s, score_pct = %s, level_awarded = %s,
               duration_sec = %s, status = 'completed', completed_at = %s
         WHERE id = %s AND status = 'in_progress'
        """,
        (
            int(correct_answers),
            round(float(score_pct), 2),
            level_awarded,
            int(duration_sec) if duration_sec is not None else None,
            _dt.datetime.now(),
            assessment_id,
        ),
    )


# ---------------------------------------------------------------------
# Per-question answers
# ---------------------------------------------------------------------
def insert_result(
    assessment_id: int,
    student_id: int,
    question_id: int,
    selected_option: int | None,
    answer_text: str | None,
    is_correct: bool,
    time_taken_sec: int | None = None,
) -> int:
    return insert(
        """
        INSERT INTO quiz_results
            (assessment_id, student_id, question_id, selected_option,
             answer_text, is_correct, time_taken_sec)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            selected_option = VALUES(selected_option),
            answer_text = VALUES(answer_text),
            is_correct = VALUES(is_correct),
            time_taken_sec = VALUES(time_taken_sec)
        """,
        (
            assessment_id,
            student_id,
            question_id,
            selected_option,
            (answer_text or "")[:2000] or None,
            1 if is_correct else 0,
            time_taken_sec,
        ),
    )


def results_for_assessment(assessment_id: int) -> list[dict]:
    return query_all(
        """
        SELECT qr.id, qr.question_id, qr.selected_option, qr.answer_text,
               qr.is_correct, qr.time_taken_sec, qr.answered_at,
               q.question_text, q.question_type, q.difficulty, q.options,
               q.correct_option, q.correct_answer, q.explanation, q.source,
               s.name AS skill_name
          FROM quiz_results qr
          JOIN questions q ON q.id = qr.question_id
          JOIN skills s ON s.id = q.skill_id
         WHERE qr.assessment_id = %s
         ORDER BY qr.id
        """,
        (assessment_id,),
    )


# ---------------------------------------------------------------------
# History / analytics
# ---------------------------------------------------------------------
def list_for_student(student_id: int, limit: int = 25) -> list[dict]:
    return query_all(
        """
        SELECT a.id, a.student_id, a.skill_id, a.assessment_type, a.total_questions,
               a.correct_answers, a.score_pct, a.level_awarded, a.duration_sec,
               a.status, a.started_at, a.completed_at, s.name AS skill_name
          FROM assessments a
          LEFT JOIN skills s ON s.id = a.skill_id
         WHERE a.student_id = %s
         ORDER BY a.started_at DESC, a.id DESC
         LIMIT %s
        """,
        (student_id, limit),
    )


def completed_history(student_id: int, limit: int = 50) -> list[dict]:
    return query_all(
        """
        SELECT a.id, a.skill_id, a.total_questions, a.correct_answers, a.score_pct,
               a.level_awarded, a.duration_sec, a.started_at, a.completed_at,
               s.name AS skill_name
          FROM assessments a
          LEFT JOIN skills s ON s.id = a.skill_id
         WHERE a.student_id = %s AND a.status = 'completed'
         ORDER BY a.completed_at, a.id
         LIMIT %s
        """,
        (student_id, limit),
    )


def last_completed_for_skill(student_id: int, skill_id: int) -> dict | None:
    return query_one(
        "SELECT * FROM assessments WHERE student_id = %s AND skill_id = %s "
        "AND status = 'completed' ORDER BY completed_at DESC, id DESC LIMIT 1",
        (student_id, skill_id),
    )


def skill_stats(student_id: int) -> list[dict]:
    """Per-skill accuracy from every completed attempt."""
    return query_all(
        """
        SELECT a.skill_id, s.name AS skill_name, s.category,
               COUNT(*) AS attempts,
               SUM(a.correct_answers) AS correct,
               SUM(a.total_questions) AS total,
               MAX(a.score_pct) AS best_score,
               AVG(a.score_pct) AS avg_score,
               MAX(a.completed_at) AS last_attempt
          FROM assessments a
          JOIN skills s ON s.id = a.skill_id
         WHERE a.student_id = %s AND a.status = 'completed'
         GROUP BY a.skill_id, s.name, s.category
         ORDER BY avg_score DESC, s.name
        """,
        (student_id,),
    )


def totals(student_id: int) -> dict:
    row = query_one(
        """
        SELECT COUNT(*) AS attempts,
               COALESCE(SUM(correct_answers), 0) AS correct,
               COALESCE(SUM(total_questions), 0) AS total,
               COALESCE(AVG(score_pct), 0) AS avg_score,
               COALESCE(MAX(score_pct), 0) AS best_score
          FROM assessments
         WHERE student_id = %s AND status = 'completed'
        """,
        (student_id,),
    ) or {}
    attempts = int(row.get("attempts") or 0)
    total = int(row.get("total") or 0)
    return {
        "attempts": attempts,
        "correct": int(row.get("correct") or 0),
        "total": total,
        "avg_score": round(float(row.get("avg_score") or 0), 1),
        "best_score": round(float(row.get("best_score") or 0), 1),
        "accuracy": round(int(row.get("correct") or 0) / total * 100, 1) if total else 0.0,
    }


def count_for_skill(student_id: int, skill_id: int) -> int:
    return int(
        scalar(
            "SELECT COUNT(*) FROM assessments WHERE student_id = %s AND skill_id = %s "
            "AND status = 'completed'",
            (student_id, skill_id),
            default=0,
        )
    )
