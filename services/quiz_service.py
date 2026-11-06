"""
Quiz + skill-assessment service (algorithms A2 and A7).

Flow
----
    start   -> abandon stale attempts, ensure >= QUIZ_MIN_QUESTIONS exist,
               create an `assessments` row (in_progress)
    load    -> return the same question set for that attempt
    submit  -> grade every answer, store `quiz_results`, close the attempt,
               map accuracy to a level (A2) and re-fuse the skill (A3)

Question selection is deterministic (validated bank first, generated
questions after it), so the in-progress attempt can be rebuilt on submit
without storing a separate question-set table.

Evidence guard rails
--------------------
* fewer than QUIZ_MIN_QUESTIONS answers -> no level, no profile update
* a template-heavy quiz is capped at level 3.0; only a session with at
  least 3 validated bank questions can award the full 1-5 band
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Any, Mapping, Sequence

from config import Config
from ml import quiz_generator
from models import assessment_model, question_model, skill_model
from services import skill_service

QUESTION_TARGET = 5
TEMPLATE_LEVEL_CAP = 3.0
VALIDATED_LEVEL_CAP = 5.0

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - optional dependency
    fuzz = None


class QuizError(Exception):
    """User-facing quiz problem (skill missing, attempt closed, ...)."""


# ---------------------------------------------------------------------
# Grading helpers
# ---------------------------------------------------------------------
def _normalise_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,;:!?\"'")


def _compact(value: str) -> str:
    """Remove spacing and brackets so '(100, 6)' == '100,6' == '[100,6]'."""
    return re.sub(r"[\s()\[\]{}]", "", value)


def grade_text(expected: Any, given: Any) -> bool:
    """Grade a free-text answer against the stored expected answer/keywords."""
    answer = _normalise_text(given)
    if not answer:
        return False

    alternatives = [part.strip() for part in str(expected or "").split("|") if part.strip()]
    if not alternatives:
        return False

    compact_answer = _compact(answer)
    for alternative in alternatives:
        target = _normalise_text(alternative)
        if not target:
            continue
        if answer == target or compact_answer == _compact(target):
            return True

        try:
            if abs(float(compact_answer) - float(_compact(target))) < 1e-9:
                return True
        except (TypeError, ValueError):
            pass

        if fuzz is not None and fuzz.WRatio(answer, target) >= 88:
            return True

        # Keyword answers: every meaningful word must appear.
        words = [w for w in re.findall(r"[a-z0-9+#.]+", target) if len(w) > 2]
        if len(words) >= 2 and all(word in answer for word in words):
            return True

    return False


def grade_question(
    question: Mapping, selected_option: int | None, answer_text: str | None
) -> tuple[bool, str | None, str | None]:
    """
    Return (is_correct, stored_option, stored_text).

    MCQ answers are graded by option index; every other type is graded by
    normalised text comparison against `correct_answer`.
    """
    if question.get("is_mcq"):
        selected = selected_option if selected_option in {0, 1, 2, 3} else None
        correct_index = question.get("correct_option")
        try:
            correct_index = int(correct_index)
        except (TypeError, ValueError):
            correct_index = -1
        return selected is not None and selected == correct_index, selected, None

    text = (answer_text or "").strip()[:2000]
    return grade_text(question.get("correct_answer"), text), None, (text or None)


def answer_display(question: Mapping, option: int | None, text: str | None) -> str:
    options = question.get("options_list") or question_model.parse_options(question)
    if question.get("is_mcq") or options:
        try:
            index = int(option)
        except (TypeError, ValueError):
            return "Not answered"
        if 0 <= index < len(options):
            return options[index]
        return "Not answered"
    return (text or "").strip() or "Not answered"


def correct_display(question: Mapping) -> str:
    options = question.get("options_list") or question_model.parse_options(question)
    if question.get("is_mcq") or options:
        try:
            index = int(question.get("correct_option"))
        except (TypeError, ValueError):
            return "See explanation"
        if 0 <= index < len(options):
            return options[index]
    return str(question.get("correct_answer") or "See explanation")


# ---------------------------------------------------------------------
# Question pool
# ---------------------------------------------------------------------
def _split_pool(questions: Sequence[dict], target: int) -> list[dict]:
    """Validated bank first, then generated questions, capped at target."""
    bank = [q for q in questions if str(q.get("source")) == "manual"]
    generated = [q for q in questions if str(q.get("source")) != "manual"]
    pool = bank[:target]
    if len(pool) < target:
        pool += generated[: target - len(pool)]
    return pool


def ensure_pool(
    skill: Mapping, target: int = QUESTION_TARGET, created_by: int | None = None
) -> tuple[list[dict], str]:
    """
    Make sure a skill has enough questions; returns (pool, note).

    The note explains a fallback so the UI can be honest about where the
    questions came from.
    """
    skill_id = int(skill["id"])
    existing = question_model.list_for_skill(skill_id)
    pool = _split_pool(existing, target)
    if len(pool) >= target:
        return pool, ""

    seen = {str(q.get("question_text") or "").strip().lower() for q in existing}
    all_skills = skill_model.list_skills()
    note = ""

    generated: list[dict] = []
    if quiz_generator.ollama_available():
        extra, note = quiz_generator.ollama_questions(skill, target - len(pool))
        generated.extend(extra)
    if not generated:
        generated.extend(quiz_generator.template_questions(skill, all_skills))
        if not note:
            note = "Questions were generated by the offline template engine."

    for item in generated:
        key = str(item.get("question_text") or "").strip().lower()
        if not key or key in seen:
            continue
        if question_model.count_for_skill(skill_id) >= target:
            break
        question_model.insert_question(
            skill_id=skill_id,
            question_type=item.get("question_type", "mcq"),
            difficulty=item.get("difficulty", "beginner"),
            question_text=item["question_text"],
            options=item.get("options"),
            correct_option=item.get("correct_option"),
            correct_answer=item.get("correct_answer"),
            explanation=item.get("explanation", ""),
            source=item.get("source", "template"),
            created_by=created_by,
        )
        seen.add(key)

    pool = _split_pool(question_model.list_for_skill(skill_id), target)
    return pool, note


def pool_for_assessment(assessment: Mapping) -> list[dict]:
    """Reconstruct the question set from the deterministic selection rule."""
    skill_id = assessment.get("skill_id")
    if not skill_id:
        return []
    try:
        target = int(assessment.get("total_questions") or QUESTION_TARGET)
    except (TypeError, ValueError):
        target = QUESTION_TARGET
    return _split_pool(question_model.list_for_skill(int(skill_id)), max(target, 1))


# ---------------------------------------------------------------------
# Attempt lifecycle
# ---------------------------------------------------------------------
def start(student_id: int, skill_id: int) -> dict:
    """Create a new quiz attempt for one skill."""
    skill = skill_model.get_skill(skill_id)
    if not skill:
        raise QuizError("That skill does not exist.")

    pool, note = ensure_pool(skill, QUESTION_TARGET, created_by=student_id)
    if len(pool) < Config.QUIZ_MIN_QUESTIONS:
        raise QuizError(
            f"Only {len(pool)} question(s) available for {skill['name']}; "
            f"at least {Config.QUIZ_MIN_QUESTIONS} are needed."
        )

    assessment_model.abandon_all_in_progress(student_id)
    has_text = any(not q.get("is_mcq") for q in pool)
    assessment_id = assessment_model.create(
        student_id=student_id,
        skill_id=int(skill_id),
        assessment_type="mixed" if has_text else "mcq",
        total_questions=len(pool),
    )

    return {
        "assessment_id": assessment_id,
        "skill": skill,
        "total": len(pool),
        "generated_note": note,
        "bank_count": sum(1 for q in pool if str(q.get("source")) == "manual"),
    }


def load_attempt(assessment_id: int, student_id: int) -> dict:
    """Data for the take-quiz page. Raises QuizError when unavailable."""
    assessment = assessment_model.get(assessment_id, student_id)
    if not assessment:
        raise QuizError("That quiz attempt was not found.")
    if assessment.get("status") == "completed":
        raise QuizError("This attempt is already completed.")

    skill = skill_model.get_skill(int(assessment.get("skill_id") or 0)) or {}
    pool = pool_for_assessment(assessment)
    if len(pool) < Config.QUIZ_MIN_QUESTIONS:
        raise QuizError("This attempt no longer has enough questions. Start a new quiz.")

    return {
        "assessment": assessment,
        "skill": skill,
        "questions": pool,
        "total": len(pool),
        "bank_count": sum(1 for q in pool if str(q.get("source")) == "manual"),
        "generated_count": sum(1 for q in pool if str(q.get("source")) != "manual"),
        "started_at": assessment.get("started_at"),
    }


def _duration_seconds(started_at: Any) -> int | None:
    if not isinstance(started_at, _dt.datetime):
        return None
    return max(0, int((_dt.datetime.now() - started_at).total_seconds()))


def submit(assessment_id: int, student_id: int, form: Mapping) -> dict:
    """Grade an attempt, persist results and update the skill profile."""
    assessment = assessment_model.get(assessment_id, student_id)
    if not assessment:
        raise QuizError("That quiz attempt was not found.")
    if assessment.get("status") != "in_progress":
        raise QuizError("This attempt is already closed.")

    skill_id = int(assessment.get("skill_id") or 0)
    skill = skill_model.get_skill(skill_id) or {}
    pool = pool_for_assessment(assessment)
    if not pool:
        raise QuizError("This attempt has no questions to grade.")

    correct = 0
    answered = 0
    for question in pool:
        qid = int(question["id"])
        if question.get("is_mcq"):
            raw = form.get(f"choice_{qid}")
            try:
                selected = int(raw) if raw is not None and str(raw).strip() != "" else None
            except (TypeError, ValueError):
                selected = None
            text = None
        else:
            selected = None
            text = str(form.get(f"text_{qid}") or "").strip()

        is_correct, stored_option, stored_text = grade_question(question, selected, text)
        if is_correct:
            correct += 1
        if stored_option is not None or stored_text:
            answered += 1
        assessment_model.insert_result(
            assessment_id=assessment_id,
            student_id=student_id,
            question_id=qid,
            selected_option=stored_option,
            answer_text=stored_text,
            is_correct=is_correct,
        )

    total = len(pool)
    score = round(correct / total * 100, 2) if total else 0.0
    level = skill_service.quiz_level_from_accuracy(score, answered)

    bank_count = sum(1 for q in pool if str(q.get("source")) == "manual")
    cap = VALIDATED_LEVEL_CAP if bank_count >= Config.QUIZ_MIN_QUESTIONS else TEMPLATE_LEVEL_CAP
    if level is not None:
        level = min(level, cap)

    assessment_model.complete(
        assessment_id=assessment_id,
        correct_answers=correct,
        score_pct=score,
        level_awarded=level,
        duration_sec=_duration_seconds(assessment.get("started_at")),
    )

    fused_before = None
    fused_after = None
    if level is not None:
        existing = skill_model.get_student_skill(student_id, skill_id) or {}
        fused_before = existing.get("current_level")
        fused, weights = skill_service.fuse_levels(
            existing.get("self_level"), existing.get("resume_level"), level
        )
        skill_model.upsert_student_skill(
            student_id=student_id,
            skill_id=skill_id,
            quiz_level=level,
            current_level=fused,
            last_source="hybrid" if len(weights) > 1 else "quiz",
        )
        fused_after = fused

    note = ""
    if answered < Config.QUIZ_MIN_QUESTIONS:
        note = (
            f"Only {answered} answer(s) submitted. At least "
            f"{Config.QUIZ_MIN_QUESTIONS} are needed before quiz evidence is stored."
        )
    elif bank_count < Config.QUIZ_MIN_QUESTIONS:
        note = (
            f"This quiz used {bank_count} validated bank question(s), so the awarded "
            f"level is capped at {TEMPLATE_LEVEL_CAP:.1f}. Template questions check "
            "recognition, not advanced proficiency."
        )

    return {
        "assessment_id": assessment_id,
        "skill": skill,
        "correct": correct,
        "total": total,
        "answered": answered,
        "score": score,
        "level": level,
        "bank_count": bank_count,
        "generated_count": total - bank_count,
        "fused_before": fused_before,
        "fused_after": fused_after,
        "note": note,
    }


# ---------------------------------------------------------------------
# Results / overview
# ---------------------------------------------------------------------
def result(assessment_id: int, student_id: int) -> dict | None:
    assessment = assessment_model.get(assessment_id, student_id)
    if not assessment or assessment.get("status") != "completed":
        return None

    review: list[dict] = []
    for row in assessment_model.results_for_assessment(assessment_id):
        row = dict(row)
        row["options_list"] = question_model.parse_options(row)
        row["is_mcq"] = str(row.get("question_type")) == "mcq"
        row["given_display"] = answer_display(row, row.get("selected_option"), row.get("answer_text"))
        row["correct_display"] = correct_display(row)
        review.append(row)

    skill = skill_model.get_skill(int(assessment.get("skill_id") or 0)) or {}
    student_skill = skill_model.get_student_skill(student_id, int(assessment.get("skill_id") or 0)) or {}

    return {
        "assessment": assessment,
        "skill": skill,
        "review": review,
        "correct": int(assessment.get("correct_answers") or 0),
        "total": int(assessment.get("total_questions") or 0),
        "score": float(assessment.get("score_pct") or 0),
        "level": assessment.get("level_awarded"),
        "student_skill": student_skill,
        "quiz_level": student_skill.get("quiz_level"),
        "current_level": student_skill.get("current_level"),
    }


def overview(student_id: int, career_id: int) -> dict:
    """Skill rows for the assessment picker: coverage + last attempt."""
    from services import gap_service

    analysis = gap_service.analyze(student_id, career_id)
    counts = question_model.count_map()
    stats = {
        int(row["skill_id"]): row
        for row in assessment_model.skill_stats(student_id)
    }

    rows: list[dict] = []
    for row in analysis["rows"]:
        skill_id = int(row["skill_id"])
        last = assessment_model.last_completed_for_skill(student_id, skill_id)
        stat = stats.get(skill_id, {})
        rows.append(
            {
                **row,
                "question_count": counts.get(skill_id, 0),
                "attempts": int(stat.get("attempts") or 0),
                "best_score": round(float(stat.get("best_score") or 0), 1) if stat else None,
                "last_score": float(last["score_pct"]) if last else None,
                "last_level": last.get("level_awarded") if last else None,
                "last_at": last.get("completed_at") if last else None,
            }
        )

    return {
        "analysis": analysis,
        "rows": rows,
        "totals": assessment_model.totals(student_id),
        "history": assessment_model.list_for_student(student_id, limit=6),
    }


def recent_history(student_id: int, limit: int = 20) -> list[dict]:
    rows = assessment_model.list_for_student(student_id, limit=limit)
    for row in rows:
        row["score"] = float(row.get("score_pct") or 0)
        row["duration_min"] = (
            round(float(row.get("duration_sec") or 0) / 60, 1) if row.get("duration_sec") else None
        )
    return rows
