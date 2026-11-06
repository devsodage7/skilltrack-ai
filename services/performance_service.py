"""
Performance analytics (algorithm A8) - read-only aggregation for charts.

Everything here is derived from stored attempts; nothing is invented. The
readiness trend is a reconstruction: quiz evidence is replayed in date order,
while the self rating and resume level are held at their current values
(because the schema keeps only the latest of those two). The UI states this
limitation explicitly.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from config import Config
from models import assessment_model, career_model, skill_model
from services import gap_service, skill_service


def _accuracy(correct: Any, total: Any) -> float:
    try:
        total_value = int(total or 0)
        correct_value = int(correct or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(correct_value / total_value * 100, 1) if total_value else 0.0


def _accuracy_band(value: float) -> str:
    if value >= 80:
        return "strong"
    if value >= 60:
        return "developing"
    if value > 0:
        return "weak"
    return "untested"


def skill_performance(student_id: int) -> list[dict]:
    """Union of attempted skills and stored skill rows, with accuracy."""
    stats = {int(row["skill_id"]): row for row in assessment_model.skill_stats(student_id)}
    current = {int(row["skill_id"]): row for row in skill_model.list_student_skills(student_id)}

    rows: list[dict] = []
    for skill_id in sorted(set(stats) | set(current)):
        stat = stats.get(skill_id, {})
        stored = current.get(skill_id, {})
        correct = int(stat.get("correct") or 0)
        total = int(stat.get("total") or 0)
        accuracy = _accuracy(correct, total)

        rows.append(
            {
                "skill_id": skill_id,
                "skill_name": stat.get("skill_name") or stored.get("skill_name") or f"Skill {skill_id}",
                "category": stat.get("category") or stored.get("skill_category") or "concept",
                "current_level": float(stored.get("current_level") or 0),
                "self_level": stored.get("self_level"),
                "resume_level": stored.get("resume_level"),
                "quiz_level": stored.get("quiz_level"),
                "attempts": int(stat.get("attempts") or 0),
                "correct": correct,
                "total": total,
                "accuracy": accuracy,
                "best_score": round(float(stat.get("best_score") or 0), 1) if stat else None,
                "avg_score": round(float(stat.get("avg_score") or 0), 1) if stat else None,
                "last_attempt": stat.get("last_attempt"),
                "band": _accuracy_band(accuracy),
            }
        )

    rows.sort(key=lambda row: (-row["accuracy"], -row["current_level"], row["skill_name"]))
    return rows


def score_trend(student_id: int, limit: int = 40) -> list[dict]:
    history = assessment_model.completed_history(student_id, limit=limit)
    return [
        {
            "label": row["completed_at"].strftime("%d %b") if row.get("completed_at") else "-",
            "date": row["completed_at"].isoformat() if row.get("completed_at") else None,
            "score": float(row.get("score_pct") or 0),
            "skill": row.get("skill_name") or "Mixed",
        }
        for row in history
    ]


def readiness_trend(student_id: int, career_id: int, max_points: int = 16) -> list[dict]:
    """
    Replay quiz evidence chronologically and recompute the readiness formula.

    Self and resume levels are current values, not historical ones - the
    schema stores only the latest value for each source.
    """
    requirements = career_model.career_requirements(career_id)
    if not requirements:
        return []

    student_skills = skill_model.list_student_skill_map(student_id)
    attempts = assessment_model.completed_history(student_id, limit=200)
    quiz_levels: dict[int, float] = {}
    points: list[dict] = []

    for attempt in attempts:
        skill_id = attempt.get("skill_id")
        level = attempt.get("level_awarded")
        if skill_id and level is not None:
            quiz_levels[int(skill_id)] = float(level)

        rows: list[dict] = []
        for req in requirements:
            req_skill_id = int(req["skill_id"])
            stored = student_skills.get(req_skill_id, {})
            quiz_level = quiz_levels.get(req_skill_id)
            if quiz_level is None:
                quiz_level = stored.get("quiz_level")
            fused, _weights = skill_service.fuse_levels(
                stored.get("self_level"), stored.get("resume_level"), quiz_level
            )
            rows.append(
                {
                    "weight": req.get("weight"),
                    "required_level": req.get("required_level"),
                    "current_level": fused,
                }
            )

        score, _ = gap_service.weighted_readiness(rows)
        points.append(
            {
                "label": attempt["completed_at"].strftime("%d %b") if attempt.get("completed_at") else "-",
                "score": score,
                "skill": attempt.get("skill_name") or "Quiz",
            }
        )

    if len(points) > max_points:
        step = len(points) / max_points
        sampled = [points[int(index * step)] for index in range(max_points - 1)]
        points = sampled + [points[-1]]

    return points


def career_readiness(student_id: int) -> list[dict]:
    rows = []
    for analysis in gap_service.analyze_all(student_id):
        career = analysis.get("career") or {}
        rows.append(
            {
                "career_id": int(career.get("id") or 0),
                "name": career.get("name") or "Career",
                "readiness": round(float(analysis.get("readiness") or 0), 1),
                "band": analysis.get("band"),
            }
        )
    return rows


def coverage(student_id: int) -> dict:
    rows = skill_model.list_student_skills(student_id)
    return {
        "total": len(rows),
        "self": sum(1 for row in rows if row.get("self_level") is not None),
        "resume": sum(1 for row in rows if row.get("resume_level") is not None),
        "quiz": sum(1 for row in rows if row.get("quiz_level") is not None),
    }


def overview(student_id: int, career_id: int) -> dict:
    career = career_model.get_career(career_id)
    skills = skill_performance(student_id)
    attempted = [row for row in skills if row["attempts"] > 0]

    strongest = sorted(attempted, key=lambda row: (-row["accuracy"], -row["current_level"]))[:3]
    weakest = sorted(attempted, key=lambda row: (row["accuracy"], row["skill_name"]))[:3]

    return {
        "totals": assessment_model.totals(student_id),
        "skills": skills,
        "attempted": attempted,
        "strongest": strongest,
        "weakest": weakest,
        "score_trend": score_trend(student_id),
        "readiness_trend": readiness_trend(student_id, career_id),
        "career_readiness": career_readiness(student_id),
        "coverage": coverage(student_id),
        "recent": assessment_model.list_for_student(student_id, limit=12),
        "career": career,
        "career_id": career_id,
        "today": _dt.date.today(),
        "bands": list(Config.READINESS_BANDS),
    }


def chart_payload(data: dict) -> dict:
    """Chart.js-ready series shared by the page and the JSON API."""
    attempted = data.get("attempted", [])[:10]
    return {
        "score_trend": {
            "labels": [row["label"] for row in data.get("score_trend", [])],
            "values": [row["score"] for row in data.get("score_trend", [])],
            "skills": [row["skill"] for row in data.get("score_trend", [])],
        },
        "skill_accuracy": {
            "labels": [row["skill_name"] for row in attempted],
            "values": [row["accuracy"] for row in attempted],
        },
        "career_readiness": {
            "labels": [row["name"] for row in data.get("career_readiness", [])],
            "values": [row["readiness"] for row in data.get("career_readiness", [])],
        },
        "readiness_trend": {
            "labels": [row["label"] for row in data.get("readiness_trend", [])],
            "values": [row["score"] for row in data.get("readiness_trend", [])],
            "skills": [row["skill"] for row in data.get("readiness_trend", [])],
        },
    }
