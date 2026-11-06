"""
SkillTrack AI - weighted gap analysis and readiness (algorithm A4).

Formulas (from the project specification)
-----------------------------------------
    Gap(i)       = max(0, Required(i) - Current(i))

    Readiness    = sum_i [ W(i) * min(Current(i), Required(i)) ]
                   --------------------------------------------- * 100
                             sum_i [ W(i) * Required(i) ]

Design rules
------------
* Missing skill row      -> Current = 0, flagged `has_evidence = False`
* None / NaN / "abc"     -> treated as 0, never crashes the page
* Negative or zero weight-> the requirement is ignored (cannot inflate)
* Zero denominator       -> readiness 0.0 with an explicit reason string
* Current > Required     -> capped at Required (extra skill cannot hide a gap)

The module has no Flask imports and no SQL of its own: it receives repository
rows, so every formula can be unit tested with plain dictionaries.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from config import Config
from models import career_model, skill_model
from services import skill_service

READINESS_BANDS: tuple[tuple[float, str], ...] = tuple(Config.READINESS_BANDS)


# ---------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------
def to_float(value: Any, default: float = 0.0) -> float:
    """Coerce anything to a finite float. NaN / inf / junk -> default."""
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number in (float("inf"), float("-inf")):
        return default
    return number


def clamp_level(value: Any) -> float:
    """Any level -> 0.0 .. 5.0."""
    return max(0.0, min(5.0, to_float(value, 0.0)))


def clamp_weight(value: Any) -> float:
    """Weights are positive; junk and negatives become 0 (ignored)."""
    return max(0.0, to_float(value, 0.0))


def compute_gap(current: Any, required: Any) -> float:
    """Gap(i) = max(0, Required(i) - Current(i))."""
    return round(max(0.0, clamp_level(required) - clamp_level(current)), 2)


def readiness_band(value: Any) -> str:
    score = to_float(value, 0.0)
    for threshold, label in READINESS_BANDS:
        if score >= threshold:
            return label
    return READINESS_BANDS[-1][1] if READINESS_BANDS else "Starting out"


# ---------------------------------------------------------------------
# Core maths on plain rows
# ---------------------------------------------------------------------
def weighted_readiness(rows: Iterable[Mapping[str, Any]]) -> tuple[float, dict]:
    """
    Return (readiness_pct, debug_totals).

    `rows` needs only three keys: weight, required_level, current_level.
    Rows with a non-positive weight or required level are skipped.
    """
    numerator = 0.0
    denominator = 0.0
    counted = 0
    skipped = 0

    for row in rows:
        weight = clamp_weight(row.get("weight"))
        required = clamp_level(row.get("required_level"))
        if weight <= 0 or required <= 0:
            skipped += 1
            continue

        current = clamp_level(row.get("current_level"))
        numerator += weight * min(current, required)
        denominator += weight * required
        counted += 1

    if denominator <= 1e-9:
        return 0.0, {
            "numerator": round(numerator, 4),
            "denominator": 0.0,
            "counted": counted,
            "skipped": skipped,
            "reason": "No weighted requirements to score against.",
        }

    score = round(numerator / denominator * 100.0, 2)
    return score, {
        "numerator": round(numerator, 4),
        "denominator": round(denominator, 4),
        "counted": counted,
        "skipped": skipped,
        "reason": "",
    }


def build_analysis(
    career: Mapping[str, Any] | None,
    requirements: Sequence[Mapping[str, Any]],
    skill_map: Mapping[int, Mapping[str, Any]],
) -> dict:
    """
    Build the full gap report for one career.

    `skill_map` is {skill_id: student_skills row} from skill_model.
    """
    rows: list[dict] = []

    for req in requirements:
        try:
            skill_id = int(req["skill_id"])
        except (KeyError, TypeError, ValueError):
            continue

        required = clamp_level(req.get("required_level"))
        weight = clamp_weight(req.get("weight"))
        stored = skill_map.get(skill_id) or {}
        current = clamp_level(stored.get("current_level"))
        has_evidence = bool(stored)

        gap_value = max(0.0, required - current)
        ratio = (current / required) if required > 0 else 1.0
        status = skill_service.strength_label(current, required) if required > 0 else "missing"

        rows.append(
            {
                "skill_id": skill_id,
                "skill_name": req.get("skill_name") or stored.get("skill_name") or f"Skill {skill_id}",
                "category": req.get("category") or stored.get("skill_category") or "concept",
                "required_level": required,
                "current_level": current,
                "weight": weight,
                "gap": round(gap_value, 2),
                "weighted_gap": round(weight * gap_value, 4),
                "ratio": round(ratio, 3),
                "status": status,
                "has_evidence": has_evidence,
                "prerequisite_skill_id": req.get("prerequisite_skill_id"),
                "self_level": clamp_level(stored.get("self_level")) if stored.get("self_level") is not None else None,
                "resume_level": clamp_level(stored.get("resume_level")) if stored.get("resume_level") is not None else None,
                "quiz_level": clamp_level(stored.get("quiz_level")) if stored.get("quiz_level") is not None else None,
                "evidence_count": int(stored.get("evidence_count") or 0),
            }
        )

    # Heaviest requirements first; ties broken by the larger gap.
    rows.sort(key=lambda r: (-r["weight"], -r["gap"], r["skill_name"]))

    readiness, totals = weighted_readiness(rows)
    counted = [r for r in rows if r["weight"] > 0 and r["required_level"] > 0]

    counts = {"strong": 0, "intermediate": 0, "weak": 0, "missing": 0}
    for row in counted:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    top_gaps = sorted(
        (r for r in counted if r["gap"] > 0),
        key=lambda r: (-r["weighted_gap"], r["gap"]),
    )

    return {
        "career": dict(career) if career else None,
        "rows": rows,
        "counted_rows": counted,
        "readiness": readiness,
        "band": readiness_band(readiness),
        "totals": totals,
        "counts": counts,
        "top_gaps": top_gaps,
        "covered": len(counted) - len(top_gaps),
        "is_complete": bool(counted) and not top_gaps,
        "no_evidence": sum(1 for r in counted if not r["has_evidence"]),
        "disclaimer": Config.RECOMMENDATION_DISCLAIMER,
    }


def projected_readiness(analysis: Mapping[str, Any], top_n: int = 3) -> dict:
    """
    "What if I close my N biggest weighted gaps?" - used on the gap page.

    Each selected skill is raised exactly to its required level.
    """
    rows = [dict(row) for row in analysis.get("rows", [])]
    gaps = analysis.get("top_gaps", [])[: max(0, top_n)]
    targets = {row["skill_id"] for row in gaps}

    for row in rows:
        if row["skill_id"] in targets:
            row["current_level"] = row["required_level"]

    score, _ = weighted_readiness(rows)
    return {
        "readiness": score,
        "band": readiness_band(score),
        "skills": [{"skill_id": g["skill_id"], "skill_name": g["skill_name"]} for g in gaps],
        "gain": round(score - to_float(analysis.get("readiness")), 2),
    }


# ---------------------------------------------------------------------
# Convenience wrappers used by the blueprints
# ---------------------------------------------------------------------
def analyze(student_id: int, career_id: int | None) -> dict:
    """Full analysis for one student + one career. Never raises on bad ids."""
    if not career_id:
        return build_analysis(None, [], {})

    career = career_model.get_career(int(career_id))
    if not career:
        return build_analysis(None, [], {})

    requirements = career_model.career_requirements(int(career_id))
    skill_map = skill_model.list_student_skill_map(student_id)
    return build_analysis(career, requirements, skill_map)


def analyze_all(student_id: int) -> list[dict]:
    """Readiness for every active career, best match first."""
    careers = {int(c["id"]): c for c in career_model.list_careers()}
    grouped: dict[int, list[dict]] = {}
    for req in career_model.all_requirements():
        grouped.setdefault(int(req["career_id"]), []).append(req)

    skill_map = skill_model.list_student_skill_map(student_id)
    analyses = [
        build_analysis(career, grouped.get(career_id, []), skill_map)
        for career_id, career in careers.items()
    ]
    analyses.sort(key=lambda a: (-a["readiness"], (a["career"] or {}).get("name", "")))
    return analyses


def readiness_snapshot(student_id: int, career_id: int | None) -> dict:
    """Small payload for dashboards and JSON endpoints."""
    analysis = analyze(student_id, career_id)
    return {
        "readiness": analysis["readiness"],
        "band": analysis["band"],
        "career": (analysis["career"] or {}).get("name"),
        "counts": analysis["counts"],
        "top_gaps": [
            {
                "skill_id": g["skill_id"],
                "skill_name": g["skill_name"],
                "gap": g["gap"],
                "weight": g["weight"],
            }
            for g in analysis["top_gaps"][:5]
        ],
    }
