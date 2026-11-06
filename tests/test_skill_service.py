"""Unit tests for evidence fusion and quiz-level mapping (algorithms A2/A3)."""

from __future__ import annotations

import pytest

from config import Config
from services import skill_service


@pytest.mark.parametrize(
    "levels,expected",
    [
        ((None, None, None), {}),
        ((3.0, None, None), {"self": 1.0}),
        ((None, 3.0, None), {"resume": 1.0}),
        ((None, None, 3.0), {"quiz": 1.0}),
        ((2.0, 3.0, None), {"self": 0.5, "resume": 0.5}),
        ((2.0, None, 3.0), {"self": 0.428571, "quiz": 0.571429}),
        ((None, 2.0, 3.0), {"resume": 0.428571, "quiz": 0.571429}),
        ((2.0, 3.0, 4.0), {"self": 0.3, "resume": 0.3, "quiz": 0.4}),
    ],
)
def test_effective_weights(levels, expected):
    assert skill_service.effective_weights(*levels) == expected


def test_fusion_is_weighted_average():
    fused, weights = skill_service.fuse_levels(2.0, 3.0, 4.0)
    assert fused == 3.1
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_fusion_renormalises_missing_sources():
    assert skill_service.fuse_levels(2.0, 4.0, None)[0] == 3.0
    assert skill_service.fuse_levels(None, None, 4.0)[0] == 4.0


def test_no_evidence_is_not_zero_ability():
    fused, weights = skill_service.fuse_levels(None, None, None)
    assert fused == 0.0
    assert weights == {}


def test_invalid_values_clamp_or_disappear():
    assert skill_service.fuse_levels(-3, 9, "2.5")[0] == 2.5
    assert skill_service.fuse_levels(None, None, "abc") == (0.0, {})


def test_fusion_is_bounded_and_monotonic():
    base = (1.0, 2.0, 3.0)
    fused, _ = skill_service.fuse_levels(*base)
    assert min(base) <= fused <= max(base)

    bumped, _ = skill_service.fuse_levels(1.0, 2.0, 4.0)
    assert bumped >= fused


def test_equal_sources_are_idempotent():
    for value in (0.0, 1.5, 2.5, 5.0):
        assert skill_service.fuse_levels(value, value, value)[0] == value


@pytest.mark.parametrize(
    "accuracy,answered,expected",
    [
        (100, 5, 5.0),
        (90, 5, 5.0),
        (89.99, 5, 4.0),
        (75, 5, 4.0),
        (74.99, 5, 3.0),
        (60, 5, 3.0),
        (59.99, 5, 2.0),
        (40, 5, 2.0),
        (39.99, 5, 1.0),
        (0, 5, 1.0),
        (80, 3, 4.0),
        (100, 2, None),
        (100, 0, None),
        (None, 5, None),
        ("abc", 5, None),
        (100, None, None),
    ],
)
def test_quiz_level_mapping(accuracy, answered, expected):
    assert skill_service.quiz_level_from_accuracy(accuracy, answered) == expected


def test_quiz_level_mapping_is_monotonic():
    previous = 0.0
    for accuracy in range(0, 101):
        level = skill_service.quiz_level_from_accuracy(accuracy, 5)
        assert level is not None
        assert level >= previous
        previous = level


def test_quiz_minimum_questions_comes_from_config():
    assert Config.QUIZ_MIN_QUESTIONS == 3
    assert skill_service.quiz_level_from_accuracy(100, 2) is None
    assert skill_service.quiz_level_from_accuracy(100, 3) == 5.0


@pytest.mark.parametrize(
    "current,required,expected",
    [
        (0, 3, "missing"),
        (1, 4, "weak"),
        (2, 4, "intermediate"),
        (3, 4, "strong"),
        (5, 5, "strong"),
        (3, 0, "missing"),
    ],
)
def test_strength_labels(current, required, expected):
    assert skill_service.strength_label(current, required) == expected
