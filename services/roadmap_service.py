"""
Personalised roadmap generator (algorithm A6).

Steps
-----
1. Take the weighted gap table for one career.
2. Keep every skill with gap > 0.
3. Respect career_skills.prerequisite_skill_id: a skill can only be scheduled
   after its prerequisite if that prerequisite is also a gap. Cycles are
   impossible in the seed data (validated) but the code still degrades safely.
4. Among the available skills, always pick the largest weighted gap first.
5. Estimate hours from the recommended free resource + a 50% practice buffer.
6. Pack skills into weeks using the student's weekly study hours.
7. Persist to learning_progress so completion survives a page reload.

No Flask and no SQL in the maths: the service only talks to repositories.
"""

from __future__ import annotations

import datetime as _dt
import heapq
from collections import defaultdict
from typing import Iterable, Mapping, Sequence

from config import Config
from models import career_model, progress_model, resource_model, student_model
from services import gap_service

PRACTICE_BUFFER = 1.5
DEFAULT_HOURS = float(Config.ROADMAP_DEFAULT_HOURS_PER_SKILL)
MAX_WEEKS = int(Config.ROADMAP_MAX_WEEKS)


# ---------------------------------------------------------------------
# Resource selection
# ---------------------------------------------------------------------
def pick_resource(resources: Sequence[Mapping], current_level: float) -> dict | None:
    """Choose the free resource that matches the student's current level."""
    if not resources:
        return None
    if current_level < 2.0:
        wanted = "beginner"
    elif current_level < 3.5:
        wanted = "intermediate"
    else:
        wanted = "advanced"

    for resource in resources:
        if resource.get("difficulty") == wanted:
            return dict(resource)
    return dict(resources[0])


def estimate_hours(resource: Mapping | None, required: float, current: float) -> float:
    """Resource hours scaled by how much of the requirement is still missing."""
    base = float((resource or {}).get("est_hours") or DEFAULT_HOURS)
    remaining = max(0.0, float(required) - float(current)) / 5.0
    return round(max(2.0, base * PRACTICE_BUFFER * max(0.35, remaining)), 1)


# ---------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------
def topological_order(gap_rows: Sequence[Mapping]) -> list[dict]:
    """
    Kahn's algorithm with a priority queue.

    Ready skills are ordered by weighted gap (weight x gap) so the most
    valuable requirement always comes first among the ones that are unlocked.
    """
    by_id = {int(row["skill_id"]): dict(row) for row in gap_rows}
    if not by_id:
        return []

    indegree = {skill_id: 0 for skill_id in by_id}
    children: dict[int, list[int]] = defaultdict(list)

    for skill_id, row in by_id.items():
        prereq = row.get("prerequisite_skill_id")
        try:
            prereq_id = int(prereq) if prereq is not None else None
        except (TypeError, ValueError):
            prereq_id = None
        if prereq_id and prereq_id in by_id and prereq_id != skill_id:
            children[prereq_id].append(skill_id)
            indegree[skill_id] += 1

    heap: list[tuple[float, int]] = [
        (-float(by_id[skill_id].get("weighted_gap") or 0), skill_id)
        for skill_id in by_id
        if indegree[skill_id] == 0
    ]
    heapq.heapify(heap)

    ordered: list[dict] = []
    while heap:
        _, skill_id = heapq.heappop(heap)
        ordered.append(by_id[skill_id])
        for child in children[skill_id]:
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(
                    heap, (-float(by_id[child].get("weighted_gap") or 0), child)
                )

    if len(ordered) < len(by_id):
        # Defensive: a cycle should never exist, but never lose a skill.
        seen = {row["skill_id"] for row in ordered}
        leftovers = sorted(
            (row for skill_id, row in by_id.items() if skill_id not in seen),
            key=lambda row: -float(row.get("weighted_gap") or 0),
        )
        ordered.extend(leftovers)

    return ordered


# ---------------------------------------------------------------------
# Week scheduling
# ---------------------------------------------------------------------
def schedule_weeks(items: Sequence[dict], weekly_hours: float) -> list[dict]:
    """
    Assign a start week to every item, packing consecutive weeks.

    A topic is never split across two weeks: if it does not fit in the
    remaining capacity, it starts on the next week. A single topic that needs
    more hours than the weekly budget simply fills its own week.
    """
    weekly = max(1.0, float(weekly_hours))
    week = 1
    used = 0.0
    overflow = False

    for item in items:
        hours = max(0.0, float(item.get("hours") or DEFAULT_HOURS))

        if used > 0 and used + hours > weekly + 1e-9:
            week += 1
            used = 0.0

        if week > MAX_WEEKS:
            overflow = True
        item["week"] = min(week, MAX_WEEKS)

        if hours >= weekly - 1e-9:
            # This topic fills the week by itself; the next one starts fresh.
            week += 1
            used = 0.0
        else:
            used += hours

    return items if not overflow else [dict(item, overflow=True) for item in items]


# ---------------------------------------------------------------------
# Plan building
# ---------------------------------------------------------------------
def build_items(
    gap_rows: Sequence[Mapping],
    resources: Mapping[int, Sequence[Mapping]],
    weekly_hours: float,
) -> list[dict]:
    """Turn gap rows into ordered, resource-linked, week-scheduled topics."""
    prepared: list[dict] = []
    for row in gap_rows:
        row = dict(row)
        skill_id = int(row["skill_id"])
        resource = pick_resource(resources.get(skill_id, []), float(row["current_level"]))
        row["resource_id"] = resource["id"] if resource else None
        row["resource"] = resource
        row["hours"] = estimate_hours(resource, row["required_level"], row["current_level"])
        prepared.append(row)

    ordered = topological_order(prepared)

    for row in ordered:
        prereq = row.get("prerequisite_skill_id")
        if prereq:
            row["why"] = f"Unlocked after {row.get('prereq_name') or 'its prerequisite'}"
        else:
            row["why"] = "No prerequisite - safe to start now"

    return schedule_weeks(ordered, weekly_hours)


def _prereq_names(rows: Iterable[Mapping], skill_names: Mapping[int, str]) -> None:
    for row in rows:
        prereq = row.get("prerequisite_skill_id")
        try:
            row["prereq_name"] = skill_names.get(int(prereq)) if prereq else None
        except (TypeError, ValueError):
            row["prereq_name"] = None


def generate(student_id: int, career_id: int, force: bool = False) -> dict | None:
    """
    Build and persist a roadmap. Returns the loaded plan, or None when the
    student already meets every requirement (nothing to schedule).
    """
    student = student_model.get_by_id(student_id) or {}
    analysis = gap_service.analyze(student_id, career_id)
    gap_rows = [row for row in analysis["rows"] if row["gap"] > 0]

    if not gap_rows:
        progress_model.clear(student_id, career_id)
        return None

    skill_names = {int(row["skill_id"]): row["skill_name"] for row in analysis["rows"]}
    _prereq_names(gap_rows, skill_names)

    resources = resource_model.list_for_skills([row["skill_id"] for row in gap_rows])
    weekly_hours = int(student.get("weekly_hours") or 10)
    items = build_items(gap_rows, resources, weekly_hours)

    existing = progress_model.list_for(student_id, career_id)
    completed = {
        int(row["skill_id"]) for row in existing if row["status"] == "completed"
    }

    progress_model.clear(student_id, career_id)
    progress_model.insert_many(
        student_id,
        career_id,
        [
            {
                "skill_id": item["skill_id"],
                "resource_id": item["resource_id"],
                "topic_title": item["skill_name"],
                "planned_hours": item["hours"],
                "week_number": item["week"],
                "status": "completed" if int(item["skill_id"]) in completed else "pending",
            }
            for item in items
        ],
    )

    return load_plan(student_id, career_id)


def load_plan(student_id: int, career_id: int) -> dict | None:
    """Read the stored roadmap and group it by week."""
    rows = progress_model.list_for(student_id, career_id)
    if not rows:
        return None

    career = career_model.get_career(career_id)
    student = student_model.get_by_id(student_id) or {}
    weekly_hours = int(student.get("weekly_hours") or 10)

    weeks: dict[int, list[dict]] = defaultdict(list)
    total_hours = 0.0
    for row in rows:
        hours = float(row.get("planned_hours") or row.get("est_hours") or DEFAULT_HOURS)
        row["hours"] = round(hours, 1)
        total_hours += hours
        weeks[int(row["week_number"])].append(row)

    grouped = [
        {
            "week": week,
            "topics": sorted(items, key=lambda item: item["skill_name"]),
            "hours": round(sum(item["hours"] for item in items), 1),
        }
        for week, items in sorted(weeks.items())
    ]

    summary = progress_model.summary(student_id, career_id)
    total_weeks = len(grouped)
    finish = _dt.date.today() + _dt.timedelta(weeks=max(total_weeks, 1))

    return {
        "career": career,
        "career_id": career_id,
        "weeks": grouped,
        "items": rows,
        "weekly_hours": weekly_hours,
        "total_hours": round(total_hours, 1),
        "total_weeks": total_weeks,
        "estimated_finish": finish,
        "progress": summary,
        "overflow": any(bool(item.get("overflow")) for item in rows),
    }


def ensure_plan(student_id: int, career_id: int) -> dict | None:
    """Load the plan; generate it on first visit."""
    plan = load_plan(student_id, career_id)
    if plan is None:
        plan = generate(student_id, career_id)
    return plan


def set_topic_status(
    student_id: int, career_id: int, progress_id: int, status: str
) -> bool:
    if status not in {"pending", "in_progress", "completed"}:
        return False
    row = progress_model.get(progress_id, student_id, career_id)
    if not row:
        return False
    progress_model.set_status(student_id, career_id, progress_id, status)
    return True


def explain_order() -> str:
    return (
        "Topics are ordered by prerequisite first, then by weighted gap "
        "(weight x gap) so the requirement with the highest impact on your "
        "readiness comes first. Hours come from the recommended free resource "
        "plus a 50% practice buffer, packed into your weekly study time."
    )
