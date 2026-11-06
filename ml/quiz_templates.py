"""
Template-based quiz generation (algorithm A7, offline fallback).

The validated bank only covers the core skills. For any other skill the
generator produces recognition-level MCQs from facts the system already
knows: the skill's category, its same-category peers and the kind of task
that category is used for. Every generated row is stored with
`source='template'` and `is_validated=0`, and the quiz service caps the
level awarded by a template-heavy attempt so these questions can never
pretend to measure advanced proficiency.

Deterministic by design: the same skill always yields the same questions,
which keeps an in-progress assessment reproducible without storing a
separate question-set table.
"""

from __future__ import annotations

import random
from typing import Mapping, Sequence

CATEGORY_LABELS: dict[str, str] = {
    "programming": "Programming language",
    "framework": "Framework or library",
    "database": "Database technology",
    "tool": "Tool or platform",
    "concept": "Core concept",
}

CATEGORY_TASKS: dict[str, str] = {
    "programming": "writing application logic and algorithms",
    "framework": "structuring a web application and its request handling",
    "database": "designing tables and writing queries to store records",
    "tool": "supporting the build, deployment or development workflow",
    "concept": "applying the underlying theory to analyse a problem",
}


def _label(category: str) -> str:
    return CATEGORY_LABELS.get(category, "Core concept")


def _task(category: str) -> str:
    return CATEGORY_TASKS.get(category, CATEGORY_TASKS["concept"])


def _pick(options: Sequence[str], correct: str, seed: int) -> tuple[list[str], int]:
    """Deterministically shuffle four options and return (options, index)."""
    values = list(dict.fromkeys(options))[:4]
    if correct not in values:
        values[-1] = correct
    rng = random.Random(seed)
    rng.shuffle(values)
    return values, values.index(correct)


def _distractors(skill: Mapping, all_skills: Sequence[Mapping], count: int, seed: int) -> list[str]:
    """Skills from *other* categories, chosen deterministically."""
    others = [
        s for s in all_skills
        if s.get("category") != skill.get("category")
        and int(s.get("id") or 0) != int(skill.get("id") or 0)
    ]
    rng = random.Random(seed)
    rng.shuffle(others)
    picked: list[str] = []
    for row in others:
        name = str(row.get("name") or "")
        if name and name not in picked:
            picked.append(name)
        if len(picked) == count:
            break
    return picked


def _peers(skill: Mapping, all_skills: Sequence[Mapping], count: int, seed: int) -> list[str]:
    peers = [
        str(s.get("name"))
        for s in all_skills
        if s.get("category") == skill.get("category")
        and int(s.get("id") or 0) != int(skill.get("id") or 0)
        and s.get("name")
    ]
    rng = random.Random(seed)
    rng.shuffle(peers)
    return peers[:count]


def generate(skill: Mapping, all_skills: Sequence[Mapping]) -> list[dict]:
    """
    Build up to four template questions for one skill.

    Returns dicts ready for question_model.insert_question:
        question_type, difficulty, question_text, options, correct_option,
        correct_answer, explanation, source
    """
    name = str(skill.get("name") or "").strip()
    if not name:
        return []

    category = str(skill.get("category") or "concept")
    skill_id = int(skill.get("id") or 0)
    correct_label = _label(category)

    questions: list[dict] = []

    # 1. Category classification --------------------------------------
    other_labels = [label for key, label in CATEGORY_LABELS.items() if key != category][:3]
    options, index = _pick([correct_label] + other_labels, correct_label, skill_id * 11 + 1)
    questions.append(
        {
            "question_type": "mcq",
            "difficulty": "beginner",
            "question_text": f"Which category best describes {name}?",
            "options": options,
            "correct_option": index,
            "correct_answer": None,
            "explanation": (
                f"{name} is listed as a {correct_label.lower()} in the SkillTrack "
                f"skill catalogue. Category: {category}."
            ),
            "source": "template",
        }
    )

    # 2. Closest related skill ----------------------------------------
    peers = _peers(skill, all_skills, 3, skill_id * 17 + 2)
    if peers:
        correct = peers[0]
        distractors = _distractors(skill, all_skills, 3, skill_id * 19 + 3)
        options, index = _pick([correct] + distractors, correct, skill_id * 23 + 4)
        questions.append(
            {
                "question_type": "mcq",
                "difficulty": "beginner",
                "question_text": f"Which of these is most closely related to {name}?",
                "options": options,
                "correct_option": index,
                "correct_answer": None,
                "explanation": (
                    f"{name} and {correct} are both {correct_label.lower()} skills, "
                    f"so they usually appear together in the same learning path."
                ),
                "source": "template",
            }
        )

    # 3. Task match ---------------------------------------------------
    correct_task = _task(category)
    other_tasks = [task for key, task in CATEGORY_TASKS.items() if key != category][:3]
    options, index = _pick([correct_task] + other_tasks, correct_task, skill_id * 29 + 5)
    questions.append(
        {
            "question_type": "mcq",
            "difficulty": "beginner",
            "question_text": f"In a project, which task would most directly use {name}?",
            "options": options,
            "correct_option": index,
            "correct_answer": None,
            "explanation": (
                f"{name} belongs to the {category} group, whose typical job is "
                f"{correct_task}."
            ),
            "source": "template",
        }
    )

    # 4. Odd one out (NOT this category) ------------------------------
    className = correct_label.lower()
    peers = _peers(skill, all_skills, 2, skill_id * 31 + 6)
    outsider = _distractors(skill, all_skills, 1, skill_id * 37 + 7)
    if len(peers) >= 2 and outsider:
        members = [name] + peers
        options, index = _pick(members + outsider, outsider[0], skill_id * 41 + 8)
        questions.append(
            {
                "question_type": "mcq",
                "difficulty": "intermediate",
                "question_text": f"Which of these is NOT a {className}?",
                "options": options,
                "correct_option": index,
                "correct_answer": None,
                "explanation": (
                    f"{outsider[0]} belongs to a different category, while "
                    f"{', '.join(members)} are all {className} skills."
                ),
                "source": "template",
            }
        )

    return questions
