"""
A2 - Quiz accuracy -> level mapping and answer grading.

Two independent checks:

1. Level mapping (`skill_service.quiz_level_from_accuracy`) is a deterministic
   rule. Every configured band boundary is tested, plus the minimum-answer
   guard, invalid input and monotonicity.
2. Text grading (`quiz_service.grade_text` / `grade_question`) is tested on a
   hand-labelled answer set covering exact matches, whitespace, brackets,
   numeric formatting, keyword answers, MCQ indices and wrong answers.

These are correctness tests of the rule, not a claim about question quality.
Question-bank validity is measured separately in A7.

Run:
    .\\.venv\\Scripts\\python.exe evaluation/a2_quiz_mapping.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config  # noqa: E402
from evaluation.common import heading, section, summary  # noqa: E402
from services import quiz_service, skill_service  # noqa: E402

MAPPING_CASES: list[tuple[str, float | None, int | None, float | None]] = [
    ("100% -> level 5", 100.0, 5, 5.0),
    ("exact 90% boundary -> 5", 90.0, 5, 5.0),
    ("89.99% -> 4", 89.99, 5, 4.0),
    ("exact 75% boundary -> 4", 75.0, 5, 4.0),
    ("74.99% -> 3", 74.99, 5, 3.0),
    ("exact 60% boundary -> 3", 60.0, 5, 3.0),
    ("59.99% -> 2", 59.99, 5, 2.0),
    ("exact 40% boundary -> 2", 40.0, 5, 2.0),
    ("39.99% -> 1", 39.99, 5, 1.0),
    ("0% -> 1", 0.0, 5, 1.0),
    ("negative accuracy clamps to band 1", -10.0, 5, 1.0),
    ("above 100% stays at level 5", 150.0, 5, 5.0),
    ("3 answers are enough", 80.0, 3, 4.0),
    ("2 answers -> no level", 100.0, 2, None),
    ("0 answers -> no level", 100.0, 0, None),
    ("missing accuracy -> no level", None, 5, None),
    ("junk accuracy -> no level", "abc", 5, None),  # type: ignore[arg-type]
    ("missing answered count -> no level", 100.0, None, None),
]

GRADING_CASES: list[tuple[str, str, str, bool]] = [
    ("bracketed list output", "[3]", "3", True),
    ("compact tuple output", "(100, 6)", "100,6", True),
    ("internal whitespace", "100,6", "100, 6", True),
    ("numeric float equivalence", "100", "100.0", True),
    ("case insensitive", "True", "true", True),
    ("trailing punctuation", "SELECT * FROM students", "select * from students;", True),
    ("keyword alternative", "plain text|cleartext", "stored as plain text", True),
    ("two required keywords", "precision recall", "precision and recall", True),
    ("short alternative", "AES|RSA", "RSA", True),
    ("wrong text", "media query", "database index", False),
    ("wrong number", "42", "43", False),
    ("empty answer", "3", "", False),
    ("empty expected answer", "", "anything", False),
    ("partial keyword does not pass", "linear regression", "logistic regression", False),
]

MCQ_CASES: list[tuple[str, int, int | None, bool]] = [
    ("correct option", 2, 2, True),
    ("wrong option", 2, 1, False),
    ("unanswered option", 2, None, False),
]

TEXT_QUESTION_CASES: list[tuple[str, str, str, bool]] = [
    ("text answer exact", "media query", "Media Query", True),
    ("text answer wrong", "media query", "database index", False),
    ("text answer empty", "media query", "", False),
]


def main() -> int:
    failures: list[str] = []
    checks = 0

    heading("A2 - Quiz level mapping and answer grading")

    section("Configured bands")
    print("Bands (minimum accuracy -> level):")
    for threshold, level in Config.QUIZ_LEVEL_BANDS:
        print(f"  {threshold:>5.1f}% -> {level:.1f}")
    print(f"Minimum answers for evidence: {Config.QUIZ_MIN_QUESTIONS}")

    descending = all(
        Config.QUIZ_LEVEL_BANDS[i][0] > Config.QUIZ_LEVEL_BANDS[i + 1][0]
        for i in range(len(Config.QUIZ_LEVEL_BANDS) - 1)
    )
    checks += 1
    print(f"{'PASS' if descending else 'FAIL'}  bands are strictly descending")
    if not descending:
        failures.append("QUIZ_LEVEL_BANDS is not strictly descending")

    section("Boundary mapping")
    for label, accuracy, answered, expected in MAPPING_CASES:
        actual = skill_service.quiz_level_from_accuracy(accuracy, answered)
        passed = actual == expected
        checks += 1
        print(f"{'PASS' if passed else 'FAIL'}  {label:<36} expected={expected} actual={actual}")
        if not passed:
            failures.append(f"mapping '{label}': expected {expected}, got {actual}")

    section("Monotonicity across the full range")
    previous = -1.0
    monotonic = True
    for accuracy in [value / 2 for value in range(0, 201)]:
        level = skill_service.quiz_level_from_accuracy(accuracy, 5)
        if level is not None and level < previous:
            monotonic = False
            break
        previous = level if level is not None else previous
    checks += 1
    print(f"{'PASS' if monotonic else 'FAIL'}  level never decreases as accuracy rises")
    if not monotonic:
        failures.append("level mapping is not monotonic")

    section("Text-answer grading")
    grading_passes = 0
    for label, expected, given, should_pass in GRADING_CASES:
        actual = quiz_service.grade_text(expected, given)
        passed = actual is should_pass
        grading_passes += int(passed)
        checks += 1
        print(
            f"{'PASS' if passed else 'FAIL'}  {label:<34} "
            f"expected={should_pass} actual={actual}"
        )
        if not passed:
            failures.append(f"grading '{label}': expected {should_pass}, got {actual}")
    print(f"Grading accuracy: {grading_passes}/{len(GRADING_CASES)} "
          f"({grading_passes / len(GRADING_CASES) * 100:.1f}%)")

    section("MCQ grading")
    for label, correct, selected, expected in MCQ_CASES:
        question = {
            "is_mcq": True,
            "correct_option": correct,
            "correct_answer": None,
        }
        is_correct, stored_option, stored_text = quiz_service.grade_question(
            question, selected, None
        )
        passed = is_correct is expected and stored_option == selected and stored_text is None
        checks += 1
        print(f"{'PASS' if passed else 'FAIL'}  {label:<36} correct={is_correct}")
        if not passed:
            failures.append(f"MCQ '{label}': expected {expected}, got {is_correct}")

    section("Free-text question grading")
    for label, expected_answer, given, should_pass in TEXT_QUESTION_CASES:
        question = {
            "is_mcq": False,
            "correct_option": None,
            "correct_answer": expected_answer,
        }
        is_correct, stored_option, stored_text = quiz_service.grade_question(
            question, None, given
        )
        passed = (
            is_correct is should_pass
            and stored_option is None
            and stored_text == (given.strip()[:2000] or None)
        )
        checks += 1
        print(f"{'PASS' if passed else 'FAIL'}  {label:<36} correct={is_correct}")
        if not passed:
            failures.append(f"text question '{label}': expected {should_pass}, got {is_correct}")

    return summary(failures, checks)


if __name__ == "__main__":
    raise SystemExit(main())
