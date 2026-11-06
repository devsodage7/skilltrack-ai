"""Unit tests for the gap/readiness engine (algorithm A4)."""

from __future__ import annotations

import math

import pytest

from services import gap_service


def test_gap_formula_and_clamping():
    assert gap_service.compute_gap(2.0, 4.0) == 2.0
    assert gap_service.compute_gap(4.0, 2.0) == 0.0
    assert gap_service.compute_gap(None, 3.0) == 3.0
    assert gap_service.compute_gap(7.0, 3.0) == 0.0
    assert gap_service.compute_gap("abc", "def") == 0.0


def test_clamp_level_handles_nan_and_infinity():
    assert gap_service.clamp_level("3.5") == 3.5
    assert gap_service.clamp_level(-2) == 0.0
    assert gap_service.clamp_level(9) == 5.0
    assert gap_service.clamp_level(float("nan")) == 0.0
    assert gap_service.clamp_level(float("inf")) == 0.0


def test_weighted_readiness_simple():
    rows = [
        {"weight": 1, "required_level": 4, "current_level": 3},
        {"weight": 1, "required_level": 2, "current_level": 0},
    ]
    score, totals = gap_service.weighted_readiness(rows)
    assert score == 50.0
    assert totals["denominator"] == 6.0
    assert totals["counted"] == 2


def test_zero_denominator_is_explicit():
    score, totals = gap_service.weighted_readiness([])
    assert score == 0.0
    assert totals["reason"]


def test_zero_weight_and_zero_requirement_are_skipped():
    rows = [
        {"weight": 0, "required_level": 5, "current_level": 5},
        {"weight": 2, "required_level": 0, "current_level": 5},
        {"weight": -1, "required_level": 5, "current_level": 5},
        {"weight": 1, "required_level": 5, "current_level": 2},
    ]
    score, totals = gap_service.weighted_readiness(rows)
    assert score == 40.0
    assert totals["counted"] == 1
    assert totals["skipped"] == 3


def test_current_above_required_is_capped():
    rows = [
        {"weight": 1, "required_level": 2, "current_level": 5},
        {"weight": 1, "required_level": 4, "current_level": 4},
    ]
    score, _ = gap_service.weighted_readiness(rows)
    assert score == 100.0


def test_invalid_values_do_not_crash():
    rows = [
        {"weight": "x", "required_level": 5, "current_level": 5},
        {"weight": 2, "required_level": "bad", "current_level": 5},
        {"weight": 2, "required_level": 3, "current_level": None},
    ]
    score, totals = gap_service.weighted_readiness(rows)
    assert score == 0.0
    assert totals["counted"] == 1


def test_build_analysis_structure_and_top_gaps():
    career = {"id": 1, "name": "Data Analyst"}
    requirements = [
        {
            "skill_id": 1, "skill_name": "SQL", "category": "programming",
            "required_level": 4, "weight": 3, "prerequisite_skill_id": None,
        },
        {
            "skill_id": 2, "skill_name": "Excel", "category": "tool",
            "required_level": 3, "weight": 1, "prerequisite_skill_id": 1,
        },
        {
            "skill_id": 3, "skill_name": "Python", "category": "programming",
            "required_level": 3, "weight": 2, "prerequisite_skill_id": None,
        },
    ]
    skill_map = {
        1: {"skill_id": 1, "current_level": 2.0, "self_level": 2.0},
        3: {"skill_id": 3, "current_level": 3.0, "self_level": 3.0},
    }

    analysis = gap_service.build_analysis(career, requirements, skill_map)

    assert analysis["career"]["name"] == "Data Analyst"
    assert analysis["readiness"] == pytest.approx(57.14, abs=0.01)
    assert analysis["counts"]["missing"] == 1
    assert analysis["counts"]["strong"] == 1
    assert [row["skill_id"] for row in analysis["top_gaps"]] == [1, 2]
    assert analysis["rows"][0]["weight"] == 3
    assert analysis["no_evidence"] == 1
    assert analysis["is_complete"] is False

    sql = next(row for row in analysis["rows"] if row["skill_id"] == 1)
    assert sql["gap"] == 2.0
    assert sql["weighted_gap"] == 6.0
    assert sql["has_evidence"] is True

    excel = next(row for row in analysis["rows"] if row["skill_id"] == 2)
    assert excel["has_evidence"] is False
    assert excel["prerequisite_skill_id"] == 1


def test_projected_readiness_closes_selected_gaps():
    requirements = [
        {"skill_id": 1, "skill_name": "A", "required_level": 5, "weight": 2},
        {"skill_id": 2, "skill_name": "B", "required_level": 4, "weight": 1},
        {"skill_id": 3, "skill_name": "C", "required_level": 3, "weight": 1},
    ]
    analysis = gap_service.build_analysis(
        {"id": 1},
        requirements,
        {1: {"current_level": 2}, 2: {"current_level": 1}, 3: {"current_level": 3}},
    )
    projected = gap_service.projected_readiness(analysis, top_n=2)
    assert projected["readiness"] == 100.0
    assert projected["gain"] > 0
    assert len(projected["skills"]) == 2


@pytest.mark.parametrize(
    "score,expected",
    [
        (100, "Career ready"),
        (85, "Career ready"),
        (84.99, "Nearly ready"),
        (70, "Nearly ready"),
        (69.99, "Developing"),
        (50, "Developing"),
        (49.99, "Foundation stage"),
        (25, "Foundation stage"),
        (0, "Starting out"),
    ],
)
def test_readiness_band_boundaries(score, expected):
    assert gap_service.readiness_band(score) == expected


def test_float_helper_is_finite():
    assert gap_service.to_float(float("inf"), 1.0) == 1.0
    assert math.isfinite(gap_service.to_float("2.5"))
