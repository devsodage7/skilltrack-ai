"""
SkillTrack AI - hybrid skill estimation (algorithm A3).

This module is the heart of the research contribution. It is deliberately
free of Flask and SQL side effects except in the two convenience helpers at
the bottom, so the maths can be unit tested in isolation.

Evidence sources
----------------
    self    -> what the student claims (0-5)
    resume  -> what the CV text proves (0-5, algorithm A1)
    quiz    -> what the assessment measured (0-5, algorithm A2)

Fusion
------
    current = sum(w_s * level_s)  over the sources that exist
    weights are renormalised so they always sum to 1 for the available set.
"""

from __future__ import annotations

from typing import Any

from config import Config
from models import skill_model

# Default weights (configurable in one place)
FUSION_WEIGHTS: dict[str, float] = dict(Config.FUSION_WEIGHTS)

SOURCE_KEYS = ("self", "resume", "quiz")

EXPLANATION = (
    "The final level blends three evidences: self assessment (30%), resume "
    "evidence (30%) and quiz performance (40%). When an evidence is missing "
    "its weight is redistributed over the remaining ones, so the result is "
    "always a weighted average, never an inflated or deflated number."
)


# ---------------------------------------------------------------------
# Core maths
# ---------------------------------------------------------------------
def clamp_level(value: Any, default: float | None = None) -> float | None:
    """Coerce any input to a 0-5 float. Invalid input -> default (or None)."""
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:  # NaN
        return default
    return max(0.0, min(5.0, number))


def effective_weights(
    self_level: float | None = None,
    resume_level: float | None = None,
    quiz_level: float | None = None,
) -> dict[str, float]:
    """
    Renormalise the default weights over the sources that actually exist.

    Examples
    --------
    all three      -> {'self': 0.30, 'resume': 0.30, 'quiz': 0.40}
    self + resume  -> {'self': 0.50, 'resume': 0.50}
    quiz only      -> {'quiz': 1.00}
    nothing        -> {}
    """
    values = {
        "self": self_level,
        "resume": resume_level,
        "quiz": quiz_level,
    }
    present = [key for key in SOURCE_KEYS if values[key] is not None]
    total = sum(FUSION_WEIGHTS[key] for key in present)

    if not present or total <= 0:
        return {}

    return {key: round(FUSION_WEIGHTS[key] / total, 6) for key in present}


def fuse_levels(
    self_level: float | None = None,
    resume_level: float | None = None,
    quiz_level: float | None = None,
) -> tuple[float, dict[str, float]]:
    """
    Return (fused_level, weights_used).

    Missing source -> weight redistributed.
    No source at all -> (0.0, {}) which callers must treat as "missing skill",
    not as "zero ability".
    """
    cleaned = {
        "self": clamp_level(self_level),
        "resume": clamp_level(resume_level),
        "quiz": clamp_level(quiz_level),
    }
    weights = effective_weights(cleaned["self"], cleaned["resume"], cleaned["quiz"])
    if not weights:
        return 0.0, {}

    score = sum(weights[key] * cleaned[key] for key in weights)  # type: ignore[operator]
    return round(score, 1), weights


def quiz_level_from_accuracy(
    accuracy_pct: float | None,
    answered: int | None,
) -> float | None:
    """
    Algorithm A2: map quiz accuracy to a 0-5 level.

    Returns None when there is not enough evidence (< QUIZ_MIN_QUESTIONS),
    which keeps a single lucky answer from inflating a profile.
    """
    if accuracy_pct is None:
        return None
    try:
        accuracy = float(accuracy_pct)
        count = int(answered or 0)
    except (TypeError, ValueError):
        return None

    if count < Config.QUIZ_MIN_QUESTIONS:
        return None

    for threshold, level in Config.QUIZ_LEVEL_BANDS:
        if accuracy >= threshold:
            return float(level)
    return 1.0


def strength_label(current_level: float | None, required_level: float | None) -> str:
    """
    Classify a skill as missing / weak / intermediate / strong.

    Uses the ratio current / required so a level 3 skill is "strong" for a
    level 3 requirement but only "intermediate" for a level 5 requirement.
    """
    current = clamp_level(current_level, 0.0) or 0.0
    required = clamp_level(required_level, 0.0) or 0.0

    if required <= 0:
        return "missing"
    if current <= 0:
        return "missing"

    ratio = current / required
    for threshold, label in Config.STRENGTH_BANDS:
        if ratio >= threshold:
            return label
    return "missing"


def readiness_explanation() -> str:
    """Human readable description used by the UI."""
    return (
        "Readiness = sum(weight x min(current, required)) / "
        "sum(weight x required) x 100. Weights come from the career "
        "requirement table; capping at the required level means extra "
        "skill in one area cannot hide a gap in another."
    )


# ---------------------------------------------------------------------
# Persistence helpers (thin wrappers, still no HTTP concerns)
# ---------------------------------------------------------------------
def set_self_level(student_id: int, skill_id: int, level: float) -> dict:
    """
    Store a self rating, re-fuse the full row and return the breakdown.

    Returns {"level": float, "weights": dict, "sources": dict}
    """
    level = clamp_level(level, 0.0) or 0.0
    existing = skill_model.get_student_skill(student_id, skill_id) or {}
    resume_level = clamp_level(existing.get("resume_level"))
    quiz_level = clamp_level(existing.get("quiz_level"))

    fused, weights = fuse_levels(level, resume_level, quiz_level)
    source = "self" if len(weights) == 1 else "hybrid"

    skill_model.upsert_student_skill(
        student_id=student_id,
        skill_id=skill_id,
        self_level=level,
        current_level=fused,
        last_source=source,
    )

    return {
        "level": fused,
        "weights": weights,
        "sources": {
            "self": level,
            "resume": resume_level,
            "quiz": quiz_level,
        },
    }


def recompute_skill(student_id: int, skill_id: int) -> float:
    """
    Re-fuse one skill row from the levels already stored in the database.
    Called after a quiz attempt or a resume upload.
    """
    row = skill_model.get_student_skill(student_id, skill_id)
    if not row:
        return 0.0

    fused, weights = fuse_levels(
        row.get("self_level"), row.get("resume_level"), row.get("quiz_level")
    )
    skill_model.upsert_student_skill(
        student_id=student_id,
        skill_id=skill_id,
        current_level=fused,
        last_source="hybrid" if len(weights) > 1 else (next(iter(weights)) if weights else "none"),
    )
    return fused


def recompute_all(student_id: int) -> int:
    """Re-fuse every skill of a student. Returns the number of rows touched."""
    rows = skill_model.list_student_skills(student_id)
    for row in rows:
        recompute_skill(student_id, int(row["skill_id"]))
    return len(rows)


def breakdown(student_id: int, skill_id: int) -> dict:
    """Explain one skill for the UI."""
    row = skill_model.get_student_skill(student_id, skill_id) or {}
    sources = {
        "self": clamp_level(row.get("self_level")),
        "resume": clamp_level(row.get("resume_level")),
        "quiz": clamp_level(row.get("quiz_level")),
    }
    fused, weights = fuse_levels(sources["self"], sources["resume"], sources["quiz"])
    return {
        "skill_id": skill_id,
        "sources": sources,
        "weights": weights,
        "current_level": fused,
    }
