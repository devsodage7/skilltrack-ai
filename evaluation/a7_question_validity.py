"""
A7 - Question-bank and generated-question validity.

This measures structural validity, not "question quality" or difficulty
calibration:

* every active bank question has the fields the grader needs
* MCQ rows have exactly four unique options and an index in range
* free-text rows have a non-empty expected answer
* the offline template generator produces valid, deterministic and unique
  questions for every skill in the catalogue
* a template-heavy quiz is capped at level 3.0 by policy

Run:
    .\\.venv\\Scripts\\python.exe evaluation/a7_question_validity.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.common import heading, load_skills, section, summary  # noqa: E402
from config import Config  # noqa: E402
from ml import quiz_templates  # noqa: E402
from models import db, question_model  # noqa: E402
from services import quiz_service  # noqa: E402


def validate_question(row: dict) -> list[str]:
    """Return a list of structural problems (empty list = valid)."""
    problems: list[str] = []
    qtype = str(row.get("question_type") or "")
    if qtype not in {"mcq", "output", "coding", "scenario"}:
        problems.append(f"unknown type {qtype!r}")
    if not str(row.get("question_text") or "").strip():
        problems.append("empty question text")
    if not str(row.get("explanation") or "").strip():
        problems.append("empty explanation")
    if str(row.get("source") or "") not in {"manual", "template", "ollama"}:
        problems.append(f"unknown source {row.get('source')!r}")

    if qtype == "mcq":
        options = row.get("options_list")
        if options is None:
            options = question_model.parse_options(row)
        if len(options) != 4:
            problems.append(f"{len(options)} options (expected 4)")
        if len(set(options)) != len(options):
            problems.append("duplicate options")
        try:
            index = int(row.get("correct_option"))
        except (TypeError, ValueError):
            problems.append("missing correct_option")
        else:
            if index < 0 or index > 3:
                problems.append(f"correct_option {index} out of range")
    else:
        if not str(row.get("correct_answer") or "").strip():
            problems.append("empty correct_answer")
    return problems


def main() -> int:
    failures: list[str] = []
    checks = 0

    skills = load_skills()
    heading("A7 - Question-bank and generated-question validity")
    print(f"Skills in catalogue: {len(skills)}")

    section("Active question bank")
    rows = db.query_all(
        """
        SELECT q.*, s.name AS skill_name
          FROM questions q
          JOIN skills s ON s.id = q.skill_id
         WHERE q.is_active = 1
         ORDER BY q.skill_id, q.id
        """
    )
    invalid: list[tuple[int, str, list[str]]] = []
    type_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    active_per_skill: Counter[int] = Counter()
    validated_per_skill: Counter[int] = Counter()
    validation_flag_errors: list[int] = []

    for row in rows:
        enriched = dict(row)
        enriched["options_list"] = question_model.parse_options(row)
        problems = validate_question(enriched)
        if problems:
            invalid.append((int(row["id"]), str(row["skill_name"]), problems))
        type_counts[str(row["question_type"])] += 1
        source_counts[str(row["source"])] += 1
        active_per_skill[int(row["skill_id"])] += 1
        if str(row["source"]) == "manual":
            validated_per_skill[int(row["skill_id"])] += 1
        expected_flag = 1 if str(row["source"]) == "manual" else 0
        if int(row.get("is_validated") or 0) != expected_flag:
            validation_flag_errors.append(int(row["id"]))

    checks += 1
    print(f"{'PASS' if not invalid else 'FAIL'}  {len(rows)} active questions checked, "
          f"{len(invalid)} invalid")
    if invalid:
        for question_id, skill_name, problems in invalid[:10]:
            print(f"    q{question_id} ({skill_name}): {', '.join(problems)}")
        failures.append(f"{len(invalid)} invalid bank questions")

    print(f"Types  : {dict(sorted(type_counts.items()))}")
    print(f"Sources: {dict(sorted(source_counts.items()))}")

    checks += 1
    print(f"{'PASS' if not validation_flag_errors else 'FAIL'}  is_validated matches source "
          f"({len(validation_flag_errors)} rows wrong)")
    if validation_flag_errors:
        failures.append(f"is_validated flag wrong on {len(validation_flag_errors)} rows")

    covered = [skill for skill in skills if validated_per_skill[int(skill["id"])] >= 3]
    partial = [skill for skill in skills if 0 < validated_per_skill[int(skill["id"])] < 3]
    empty = [skill for skill in skills if validated_per_skill[int(skill["id"])] == 0]
    active_covered = [skill for skill in skills if active_per_skill[int(skill["id"])] >= 3]
    print(f"Skills with >=3 validated bank questions: {len(covered)}/{len(skills)}")
    print(f"Skills with 1-2 validated questions     : {len(partial)}")
    print(f"Skills with 0 validated questions       : {len(empty)}")
    print(f"Skills with >=3 active questions (bank + generated): {len(active_covered)}/{len(skills)}")

    section("Offline template generation for every skill")
    total_generated = 0
    generation_failures: list[str] = []
    nondeterministic: list[str] = []
    duplicate_within_skill: list[str] = []
    all_texts: list[str] = []
    minimum_count = 99
    maximum_count = 0

    for skill in skills:
        first = quiz_templates.generate(skill, skills)
        second = quiz_templates.generate(skill, skills)
        total_generated += len(first)
        minimum_count = min(minimum_count, len(first))
        maximum_count = max(maximum_count, len(first))

        if first != second:
            nondeterministic.append(str(skill["name"]))

        if len(first) < 3:
            generation_failures.append(
                f"{skill['name']}: only {len(first)} template questions"
            )

        texts = [str(item.get("question_text") or "") for item in first]
        if len(set(texts)) != len(texts):
            duplicate_within_skill.append(str(skill["name"]))
        all_texts.extend(texts)

        for index, item in enumerate(first):
            problems = validate_question({**item, "options_list": item.get("options")})
            if problems:
                generation_failures.append(
                    f"{skill['name']} template {index + 1}: {', '.join(problems)}"
                )

    checks += 1
    print(f"{'PASS' if not generation_failures else 'FAIL'}  {total_generated} template questions "
          f"generated, {len(generation_failures)} invalid")
    if generation_failures:
        for item in generation_failures[:10]:
            print(f"    {item}")
        failures.append(f"{len(generation_failures)} invalid template questions")

    checks += 1
    print(f"{'PASS' if minimum_count >= 3 else 'FAIL'}  every skill gets at least 3 template questions "
          f"(min={minimum_count}, max={maximum_count})")
    if minimum_count < 3:
        failures.append(f"minimum template question count is {minimum_count}")

    checks += 1
    print(f"{'PASS' if not nondeterministic else 'FAIL'}  generation is deterministic "
          f"({len(nondeterministic)} mismatches)")
    if nondeterministic:
        failures.append(f"non-deterministic generation: {nondeterministic[:5]}")

    checks += 1
    print(f"{'PASS' if not duplicate_within_skill else 'FAIL'}  no duplicate question text within a skill "
          f"({len(duplicate_within_skill)} skills affected)")
    if duplicate_within_skill:
        failures.append(f"duplicate text within: {duplicate_within_skill[:5]}")

    checks += 1
    duplicates_across = len(all_texts) - len(set(all_texts))
    print(f"INFO  {duplicates_across} template texts repeat across skills (generic category "
          f"wording; every quiz is single-skill, so they are never mixed in one attempt)")

    section("Level-cap policy")
    print("Validated bank questions in the pool -> maximum level that can be awarded:")
    expected_caps = [(0, 3.0), (1, 3.0), (2, 3.0), (3, 5.0), (5, 5.0)]
    for bank_count, expected in expected_caps:
        actual = (
            quiz_service.VALIDATED_LEVEL_CAP
            if bank_count >= Config.QUIZ_MIN_QUESTIONS
            else quiz_service.TEMPLATE_LEVEL_CAP
        )
        checks += 1
        passed = actual == expected
        print(f"{'PASS' if passed else 'FAIL'}  {bank_count} validated -> cap {actual:.1f}")
        if not passed:
            failures.append(f"cap for {bank_count} validated questions is {actual}")

    return summary(failures, checks)


if __name__ == "__main__":
    raise SystemExit(main())
