"""Unit tests for DAG ordering and week scheduling (algorithm A6)."""

from __future__ import annotations

from config import Config
from services import roadmap_service


def test_prerequisite_before_dependent():
    rows = [
        {"skill_id": 1, "weighted_gap": 1.0, "prerequisite_skill_id": None},
        {"skill_id": 2, "weighted_gap": 9.0, "prerequisite_skill_id": 1},
        {"skill_id": 3, "weighted_gap": 5.0, "prerequisite_skill_id": 1},
    ]
    ordered = [row["skill_id"] for row in roadmap_service.topological_order(rows)]
    assert ordered.index(1) < ordered.index(2)
    assert ordered.index(1) < ordered.index(3)


def test_highest_weighted_gap_first_among_unlocked():
    rows = [
        {"skill_id": 1, "weighted_gap": 1.0, "prerequisite_skill_id": None},
        {"skill_id": 2, "weighted_gap": 9.0, "prerequisite_skill_id": 1},
        {"skill_id": 3, "weighted_gap": 5.0, "prerequisite_skill_id": None},
    ]
    ordered = [row["skill_id"] for row in roadmap_service.topological_order(rows)]
    assert ordered[0] == 3
    assert ordered.index(1) < ordered.index(2)


def test_cycle_never_loses_skills():
    rows = [
        {"skill_id": 1, "weighted_gap": 1.0, "prerequisite_skill_id": 2},
        {"skill_id": 2, "weighted_gap": 2.0, "prerequisite_skill_id": 1},
        {"skill_id": 3, "weighted_gap": 3.0, "prerequisite_skill_id": 3},
    ]
    ordered = [row["skill_id"] for row in roadmap_service.topological_order(rows)]
    assert set(ordered) == {1, 2, 3}
    assert len(ordered) == 3


def test_missing_prerequisite_is_treated_as_unlocked():
    rows = [
        {"skill_id": 10, "weighted_gap": 2.0, "prerequisite_skill_id": 99},
        {"skill_id": 11, "weighted_gap": 1.0, "prerequisite_skill_id": None},
    ]
    ordered = [row["skill_id"] for row in roadmap_service.topological_order(rows)]
    assert set(ordered) == {10, 11}


def test_schedule_packs_topics_without_splitting():
    items = [
        {"skill_id": 1, "hours": 6.0},
        {"skill_id": 2, "hours": 4.0},
        {"skill_id": 3, "hours": 8.0},
        {"skill_id": 4, "hours": 3.0},
    ]
    scheduled = roadmap_service.schedule_weeks(items, 10.0)
    assert [item["week"] for item in scheduled] == [1, 1, 2, 3]


def test_oversized_topic_gets_its_own_week():
    items = [{"skill_id": 1, "hours": 12.0}, {"skill_id": 2, "hours": 3.0}]
    scheduled = roadmap_service.schedule_weeks(items, 5.0)
    assert [item["week"] for item in scheduled] == [1, 2]


def test_overflow_is_flagged_and_capped():
    items = [{"skill_id": index, "hours": 10.0} for index in range(1, 40)]
    scheduled = roadmap_service.schedule_weeks(items, 10.0)
    assert all(item.get("overflow") for item in scheduled)
    assert max(item["week"] for item in scheduled) == Config.ROADMAP_MAX_WEEKS


def test_empty_schedule():
    assert roadmap_service.schedule_weeks([], 8.0) == []


def test_pick_resource_by_current_level():
    resources = [
        {"id": 1, "difficulty": "beginner", "est_hours": 10},
        {"id": 2, "difficulty": "intermediate", "est_hours": 20},
        {"id": 3, "difficulty": "advanced", "est_hours": 30},
    ]
    assert roadmap_service.pick_resource(resources, 0.0)["id"] == 1
    assert roadmap_service.pick_resource(resources, 2.9)["id"] == 2
    assert roadmap_service.pick_resource(resources, 4.0)["id"] == 3
    assert roadmap_service.pick_resource([], 2.0) is None


def test_estimate_hours_has_floor_and_practice_buffer():
    resource = {"est_hours": 10}
    hours = roadmap_service.estimate_hours(resource, required=5.0, current=0.0)
    assert hours >= 2.0
    assert hours == 15.0  # 10 * 1.5 * 1.0

    small = roadmap_service.estimate_hours({"est_hours": 1}, required=1.0, current=0.9)
    assert small == 2.0


def test_default_hours_when_resource_missing():
    hours = roadmap_service.estimate_hours(None, required=5.0, current=0.0)
    assert hours == round(Config.ROADMAP_DEFAULT_HOURS_PER_SKILL * 1.5, 1)
