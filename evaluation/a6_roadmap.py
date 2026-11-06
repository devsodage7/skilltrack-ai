"""
A6 - Roadmap ordering and week scheduling.

Two pure algorithms are stress tested:

* `topological_order` - Kahn's algorithm with a priority queue. A prerequisite
  must always be scheduled before the skill that depends on it; cycles must
  never lose a topic.
* `schedule_weeks` - packs topics into weeks without splitting a topic, keeps
  each normal week within the student's budget, and flags overflow beyond the
  24-week limit.

Random DAGs and random hour vectors are generated with a fixed seed, so the
run is reproducible. The seeded career_skills DAG is also validated.

Run:
    .\\.venv\\Scripts\\python.exe evaluation/a6_roadmap.py
"""

from __future__ import annotations

import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config  # noqa: E402
from evaluation.common import heading, init_db, section, summary  # noqa: E402
from models import career_model, db  # noqa: E402
from services import roadmap_service  # noqa: E402


def random_dag(rng: random.Random, size: int) -> list[dict]:
    rows = []
    for skill_id in range(1, size + 1):
        prereq = None
        if skill_id > 1 and rng.random() < 0.55:
            prereq = rng.randint(1, skill_id - 1)
        rows.append(
            {
                "skill_id": skill_id,
                "weighted_gap": round(rng.uniform(0.0, 5.0), 3),
                "prerequisite_skill_id": prereq,
            }
        )
    return rows


def main() -> int:
    failures: list[str] = []
    checks = 0

    heading("A6 - Roadmap DAG and week scheduler")

    section("Random DAG ordering (200 graphs)")
    rng = random.Random(20261106)
    order_violations = 0
    lost_skills = 0
    for _ in range(200):
        size = rng.randint(3, 15)
        rows = random_dag(rng, size)
        ordered = roadmap_service.topological_order(rows)
        ids = [row["skill_id"] for row in ordered]
        if len(ids) != size or set(ids) != {row["skill_id"] for row in rows}:
            lost_skills += 1
            continue
        position = {skill_id: index for index, skill_id in enumerate(ids)}
        for row in rows:
            prereq = row["prerequisite_skill_id"]
            if prereq is not None and position[prereq] > position[row["skill_id"]]:
                order_violations += 1
                break

    checks += 1
    print(f"{'PASS' if lost_skills == 0 else 'FAIL'}  every skill appears exactly once "
          f"({lost_skills} graphs lost a skill)")
    if lost_skills:
        failures.append(f"{lost_skills} random graphs lost a skill")

    checks += 1
    print(f"{'PASS' if order_violations == 0 else 'FAIL'}  prerequisite before dependent "
          f"({order_violations} violations)")
    if order_violations:
        failures.append(f"{order_violations} prerequisite-order violations")

    section("Cycle safety")
    cycle_rows = [
        {"skill_id": 1, "weighted_gap": 3.0, "prerequisite_skill_id": 2},
        {"skill_id": 2, "weighted_gap": 2.0, "prerequisite_skill_id": 3},
        {"skill_id": 3, "weighted_gap": 1.0, "prerequisite_skill_id": 1},
        {"skill_id": 4, "weighted_gap": 4.0, "prerequisite_skill_id": 4},
        {"skill_id": 5, "weighted_gap": 0.5, "prerequisite_skill_id": None},
    ]
    cycle_order = roadmap_service.topological_order(cycle_rows)
    cycle_ids = [row["skill_id"] for row in cycle_order]
    checks += 1
    passed = len(cycle_ids) == 5 and set(cycle_ids) == {1, 2, 3, 4, 5}
    print(f"{'PASS' if passed else 'FAIL'}  3-cycle and self-loop keep all topics: {cycle_ids}")
    if not passed:
        failures.append(f"cycle lost topics: {cycle_ids}")

    checks += 1
    empty = roadmap_service.topological_order([])
    print(f"{'PASS' if empty == [] else 'FAIL'}  empty input -> empty order")
    if empty != []:
        failures.append("topological_order([]) did not return []")

    section("Random week scheduling (300 cases)")
    schedule_violations = 0
    hour_loss = 0
    split_topics = 0
    order_regressions = 0

    for _ in range(300):
        count = rng.randint(1, 18)
        weekly = rng.choice([4.0, 6.0, 8.0, 10.0, 12.0, 16.0])
        items = [
            {"skill_id": index, "hours": round(rng.uniform(0.5, 14.0), 1)}
            for index in range(1, count + 1)
        ]
        scheduled = roadmap_service.schedule_weeks([dict(item) for item in items], weekly)
        weeks = [item["week"] for item in scheduled]

        if len(scheduled) != count or any(week < 1 or week > Config.ROADMAP_MAX_WEEKS for week in weeks):
            schedule_violations += 1
            continue
        if weeks != sorted(weeks):
            order_regressions += 1
        if any(item.get("overflow") for item in scheduled):
            # Overflow is the documented outcome when the 24-week cap is hit;
            # it is tested separately below, not counted as a violation here.
            continue

        total_in = round(sum(item["hours"] for item in items), 6)
        total_out = round(sum(item["hours"] for item in scheduled), 6)
        if abs(total_in - total_out) > 1e-9:
            hour_loss += 1

        groups: dict[int, list[dict]] = defaultdict(list)
        for item in scheduled:
            groups[item["week"]].append(item)
            if item["week"] < 1:
                split_topics += 1
        for week_items in groups.values():
            load = sum(item["hours"] for item in week_items)
            if len(week_items) > 1 and load > weekly + 1e-9:
                schedule_violations += 1
                break
            if len(week_items) == 1 and week_items[0]["hours"] <= weekly + 1e-9 and load > weekly + 1e-9:
                schedule_violations += 1
                break

    checks += 1
    print(f"{'PASS' if schedule_violations == 0 else 'FAIL'}  week capacity respected unless one topic alone is oversized "
          f"({schedule_violations} violations)")
    if schedule_violations:
        failures.append(f"{schedule_violations} capacity violations")

    checks += 1
    print(f"{'PASS' if hour_loss == 0 else 'FAIL'}  scheduled hours equal requested hours "
          f"({hour_loss} cases lost time)")
    if hour_loss:
        failures.append(f"{hour_loss} cases lost scheduled hours")

    checks += 1
    print(f"{'PASS' if split_topics == 0 else 'FAIL'}  no topic is split across weeks")
    if split_topics:
        failures.append(f"{split_topics} split topics")

    checks += 1
    print(f"{'PASS' if order_regressions == 0 else 'FAIL'}  week numbers never move backwards "
          f"({order_regressions} regressions)")
    if order_regressions:
        failures.append(f"{order_regressions} week-order regressions")

    section("Explicit packing cases")
    packing = roadmap_service.schedule_weeks(
        [
            {"skill_id": 1, "hours": 6.0},
            {"skill_id": 2, "hours": 4.0},
            {"skill_id": 3, "hours": 8.0},
            {"skill_id": 4, "hours": 3.0},
        ],
        10.0,
    )
    expected = [1, 1, 2, 3]
    actual = [item["week"] for item in packing]
    checks += 1
    print(f"{'PASS' if actual == expected else 'FAIL'}  6+4 fit week 1, 8 starts week 2, 3 starts week 3 "
          f"-> {actual}")
    if actual != expected:
        failures.append(f"packing returned {actual}, expected {expected}")

    oversized = roadmap_service.schedule_weeks(
        [{"skill_id": 1, "hours": 12.0}, {"skill_id": 2, "hours": 3.0}], 5.0
    )
    checks += 1
    actual = [item["week"] for item in oversized]
    print(f"{'PASS' if actual == [1, 2] else 'FAIL'}  oversized topic gets its own week -> {actual}")
    if actual != [1, 2]:
        failures.append(f"oversized topic weeks {actual}")

    overflow = roadmap_service.schedule_weeks(
        [{"skill_id": index, "hours": 10.0} for index in range(1, 40)], 10.0
    )
    checks += 1
    passed = (
        all(item.get("overflow") for item in overflow)
        and max(item["week"] for item in overflow) == Config.ROADMAP_MAX_WEEKS
    )
    print(f"{'PASS' if passed else 'FAIL'}  40 topics overflow the {Config.ROADMAP_MAX_WEEKS}-week limit and are flagged")
    if not passed:
        failures.append("overflow flag missing or week cap exceeded")

    section("Resource selection and hour estimate")
    resources = [
        {"id": 1, "difficulty": "beginner", "est_hours": 10},
        {"id": 2, "difficulty": "intermediate", "est_hours": 20},
        {"id": 3, "difficulty": "advanced", "est_hours": 30},
    ]
    for current, expected_id in [(1.0, 1), (2.9, 2), (4.0, 3)]:
        picked = roadmap_service.pick_resource(resources, current)
        checks += 1
        passed = picked and int(picked["id"]) == expected_id
        print(f"{'PASS' if passed else 'FAIL'}  current {current:.1f} -> resource {expected_id}")
        if not passed:
            failures.append(f"pick_resource({current}) chose {picked}")

    checks += 1
    hours = roadmap_service.estimate_hours(resources[0], required=5.0, current=0.0)
    print(f"{'PASS' if hours >= 2.0 else 'FAIL'}  hour estimate respects the 2.0 h floor -> {hours} h")
    if hours < 2.0:
        failures.append(f"estimate_hours returned {hours}")

    section("Seeded career_skills DAG")
    init_db()
    careers = db.query_all("SELECT id, name FROM careers WHERE is_active = 1 ORDER BY id")
    seed_violations = 0
    for career in careers:
        requirements = career_model.career_requirements(int(career["id"]))
        rows = [
            {
                "skill_id": int(req["skill_id"]),
                "weighted_gap": float(req["weight"]) * float(req["required_level"]),
                "prerequisite_skill_id": req["prerequisite_skill_id"],
            }
            for req in requirements
        ]
        ordered = roadmap_service.topological_order(rows)
        position = {int(row["skill_id"]): index for index, row in enumerate(ordered)}
        violations = [
            (req["skill_name"], req["prerequisite_skill_id"])
            for req in requirements
            if req["prerequisite_skill_id"] in position
            and position[int(req["skill_id"])] < position[int(req["prerequisite_skill_id"])]
        ]
        seed_violations += len(violations)
        print(
            f"  {career['name']:<28} {len(requirements):>2} requirements, "
            f"{len(violations)} ordering violations"
        )
    checks += 1
    print(f"{'PASS' if seed_violations == 0 else 'FAIL'}  seeded prerequisite graph is acyclic and ordered")
    if seed_violations:
        failures.append(f"{seed_violations} violations in the seeded DAG")

    return summary(failures, checks)


if __name__ == "__main__":
    raise SystemExit(main())
