"""
A4 - Gap and readiness formula verification.

    Gap(i)    = max(0, Required(i) - Current(i))
    Readiness = sum(W * min(Current, Required)) / sum(W * Required) * 100

The implementation is compared against an independent reference implementation
written in this file, over randomised matrices plus explicit edge cases
(missing rows, invalid numbers, zero weights, zero denominator, current above
required). The real seeded data is also checked career by career.

Run:
    .\\.venv\\Scripts\\python.exe evaluation/a4_gap_readiness.py
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.common import heading, init_db, section, summary  # noqa: E402
from models import db  # noqa: E402
from services import gap_service  # noqa: E402


def num(value, default: float = 0.0) -> float:
    """Independent numeric coercion used by the reference implementation."""
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def clamp(value) -> float:
    return max(0.0, min(5.0, num(value)))


def ref_readiness(rows: list[dict]) -> tuple[float, int]:
    numerator = 0.0
    denominator = 0.0
    counted = 0
    for row in rows:
        weight = max(0.0, num(row.get("weight")))
        required = clamp(row.get("required_level"))
        if weight <= 0 or required <= 0:
            continue
        current = clamp(row.get("current_level"))
        numerator += weight * min(current, required)
        denominator += weight * required
        counted += 1
    if denominator <= 1e-9:
        return 0.0, counted
    return round(numerator / denominator * 100.0, 2), counted


def random_rows(rng: random.Random, count: int) -> list[dict]:
    rows: list[dict] = []
    for index in range(1, count + 1):
        weight = rng.choice([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, -1.0, None, "abc"])
        required = rng.choice([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, -2.0, None, "x"])
        current = rng.choice([0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 8.0, -1.0, None])
        rows.append(
            {
                "skill_id": index,
                "skill_name": f"Skill {index}",
                "category": "concept",
                "weight": weight,
                "required_level": required,
                "current_level": current,
                "prerequisite_skill_id": None,
            }
        )
    return rows


def main() -> int:
    failures: list[str] = []
    checks = 0

    heading("A4 - Gap and readiness formula")
    checks += 1
    gap_ok = (
        gap_service.compute_gap(2.0, 4.0) == 2.0
        and gap_service.compute_gap(4.0, 2.0) == 0.0
        and gap_service.compute_gap(None, 3.0) == 3.0
        and gap_service.compute_gap(7.0, 3.0) == 0.0
        and gap_service.compute_gap("abc", "def") == 0.0
    )
    print(f"{'PASS' if gap_ok else 'FAIL'}  Gap examples: max(0, required - current), clamp 0..5")
    if not gap_ok:
        failures.append("compute_gap examples failed")

    section("Explicit formula edge cases")
    edge_cases: list[tuple[str, list[dict], float]] = [
        ("empty matrix", [], 0.0),
        ("all weights zero", [{"weight": 0, "required_level": 3, "current_level": 3}], 0.0),
        ("all requirements zero", [{"weight": 2, "required_level": 0, "current_level": 5}], 0.0),
        ("negative weight ignored", [
            {"weight": -5, "required_level": 5, "current_level": 0},
            {"weight": 1, "required_level": 5, "current_level": 2},
        ], 40.0),
        ("current above required is capped", [
            {"weight": 1, "required_level": 2, "current_level": 5},
            {"weight": 1, "required_level": 4, "current_level": 4},
        ], 100.0),
        ("one missing skill", [
            {"weight": 1, "required_level": 4, "current_level": 3},
            {"weight": 1, "required_level": 2, "current_level": 0},
        ], 50.0),
        ("invalid values are zero", [
            {"weight": "x", "required_level": 5, "current_level": 5},
            {"weight": 2, "required_level": "bad", "current_level": 5},
            {"weight": 2, "required_level": 3, "current_level": None},
        ], 0.0),
    ]
    for label, rows, expected in edge_cases:
        actual, totals = gap_service.weighted_readiness(rows)
        reference, _ = ref_readiness(rows)
        passed = abs(actual - expected) < 1e-9 and abs(actual - reference) < 1e-9
        checks += 1
        print(f"{'PASS' if passed else 'FAIL'}  {label:<36} readiness={actual:>6.2f}% expected={expected:>6.2f}%")
        if not passed:
            failures.append(f"edge case '{label}': {actual} vs {expected}")

    section("Randomised matrices (800 cases)")
    rng = random.Random(20261106)
    max_error = 0.0
    max_gap_error = 0.0
    counted_mismatches = 0
    count_mismatches = 0

    for _ in range(800):
        rows = random_rows(rng, rng.randint(0, 8))
        career = {"id": 99, "name": "Synthetic Career"}
        skill_map = {
            row["skill_id"]: {
                "skill_id": row["skill_id"],
                "self_level": row["current_level"],
                "current_level": row["current_level"],
            }
            for row in rows
            if rng.random() > 0.25
        }
        requirements = [
            {**row, "skill_id": row["skill_id"]} for row in rows
        ]

        analysis = gap_service.build_analysis(career, requirements, skill_map)
        reference_score, reference_counted = ref_readiness(analysis["rows"])
        max_error = max(max_error, abs(analysis["readiness"] - reference_score))
        if abs(analysis["readiness"] - reference_score) > 0.011:
            failures.append(
                f"readiness mismatch: {analysis['readiness']} vs {reference_score}"
            )

        for row in analysis["rows"]:
            expected_gap = round(
                max(0.0, clamp(row["required_level"]) - clamp(row["current_level"])), 2
            )
            max_gap_error = max(max_gap_error, abs(row["gap"] - expected_gap))
            if abs(row["gap"] - expected_gap) > 1e-9:
                failures.append(f"gap mismatch for {row['skill_id']}: {row['gap']} vs {expected_gap}")

        if len(analysis["counted_rows"]) != reference_counted:
            counted_mismatches += 1
        if sum(analysis["counts"].values()) != len(analysis["counted_rows"]):
            count_mismatches += 1

        top_sorted = all(
            analysis["top_gaps"][i]["weighted_gap"] >= analysis["top_gaps"][i + 1]["weighted_gap"]
            for i in range(len(analysis["top_gaps"]) - 1)
        )
        if not top_sorted:
            failures.append("top_gaps is not sorted by weighted gap")

    checks += 1
    print(f"{'PASS' if max_error <= 0.011 else 'FAIL'}  max |readiness - reference| = {max_error:.6f}")
    if max_error > 0.011:
        failures.append(f"readiness error {max_error}")

    checks += 1
    print(f"{'PASS' if max_gap_error <= 1e-9 else 'FAIL'}  max |gap - reference| = {max_gap_error:.6f}")
    if max_gap_error > 1e-9:
        failures.append(f"gap error {max_gap_error}")

    checks += 1
    print(f"{'PASS' if counted_mismatches == 0 else 'FAIL'}  counted-row agreement ({counted_mismatches} mismatches)")
    if counted_mismatches:
        failures.append(f"{counted_mismatches} counted-row mismatches")

    checks += 1
    print(f"{'PASS' if count_mismatches == 0 else 'FAIL'}  status counts add up ({count_mismatches} mismatches)")
    if count_mismatches:
        failures.append(f"{count_mismatches} status-count mismatches")

    section("Projection: close the top gaps")
    projected_rows = [
        {"skill_id": 1, "skill_name": "A", "weight": 2.0, "required_level": 5.0, "current_level": 2.0},
        {"skill_id": 2, "skill_name": "B", "weight": 1.0, "required_level": 4.0, "current_level": 1.0},
        {"skill_id": 3, "skill_name": "C", "weight": 1.0, "required_level": 3.0, "current_level": 3.0},
    ]
    analysis = gap_service.build_analysis(
        {"id": 1, "name": "Test"},
        projected_rows,
        {1: {"current_level": 2.0}, 2: {"current_level": 1.0}, 3: {"current_level": 3.0}},
    )
    projected = gap_service.projected_readiness(analysis, top_n=2)
    manual_rows = [dict(row) for row in projected_rows]
    manual_rows[0]["current_level"] = 5.0
    manual_rows[1]["current_level"] = 4.0
    manual_score, _ = ref_readiness(manual_rows)
    passed = (
        abs(projected["readiness"] - manual_score) < 0.011
        and projected["gain"] > 0
        and len(projected["skills"]) == 2
    )
    checks += 1
    print(
        f"{'PASS' if passed else 'FAIL'}  current={analysis['readiness']:.2f}% -> "
        f"projected={projected['readiness']:.2f}% (manual {manual_score:.2f}%), "
        f"gain={projected['gain']:+.2f}"
    )
    if not passed:
        failures.append("projected readiness does not match the reference")

    section("Seeded database snapshot")
    init_db()
    students = db.query_all(
        "SELECT id, full_name FROM students WHERE role = 'student' ORDER BY id LIMIT 3"
    )
    if not students:
        failures.append("no seeded students found (run database/init_db.py --reset)")
    else:
        for student in students:
            analyses = gap_service.analyze_all(int(student["id"]))
            descending = all(
                analyses[i]["readiness"] >= analyses[i + 1]["readiness"]
                for i in range(len(analyses) - 1)
            )
            checks += 1
            print(
                f"{'PASS' if descending else 'FAIL'}  {student['full_name']}: "
                f"{len(analyses)} careers, best={analyses[0]['career']['name']} "
                f"{analyses[0]['readiness']:.1f}%"
            )
            if not descending:
                failures.append(f"analyze_all not sorted for student {student['id']}")

            for analysis in analyses:
                map_rows = [
                    {
                        "weight": row["weight"],
                        "required_level": row["required_level"],
                        "current_level": row["current_level"],
                    }
                    for row in analysis["rows"]
                ]
                reference_score, _ = ref_readiness(map_rows)
                if abs(analysis["readiness"] - reference_score) > 0.011:
                    failures.append(
                        f"DB readiness mismatch student {student['id']} "
                        f"career {analysis['career']['id']}: "
                        f"{analysis['readiness']} vs {reference_score}"
                    )

        print()
        print("Example: student 2 career readiness")
        for analysis in gap_service.analyze_all(2):
            print(
                f"  {analysis['career']['name']:<28} "
                f"{analysis['readiness']:>6.2f}%  {analysis['band']}"
            )

    return summary(failures, checks)


if __name__ == "__main__":
    raise SystemExit(main())
