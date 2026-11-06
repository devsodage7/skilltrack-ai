"""Unit tests for quiz grading, question selection and template generation."""

from __future__ import annotations

import pytest

from ml import quiz_templates
from services import quiz_service


@pytest.mark.parametrize(
    "expected,given,should_pass",
    [
        ("[3]", "3", True),
        ("(100, 6)", "100,6", True),
        ("100,6", "100, 6", True),
        ("100", "100.0", True),
        ("True", "true", True),
        ("SELECT * FROM students", "select * from students;", True),
        ("plain text|cleartext", "stored as plain text", True),
        ("precision recall", "precision and recall", True),
        ("AES|RSA", "RSA", True),
        ("media query", "database index", False),
        ("42", "43", False),
        ("3", "", False),
        ("", "anything", False),
        ("linear regression", "logistic regression", False),
    ],
)
def test_grade_text(expected, given, should_pass):
    assert quiz_service.grade_text(expected, given) is should_pass


def test_grade_mcq_by_index():
    question = {"is_mcq": True, "correct_option": 2, "correct_answer": None}
    assert quiz_service.grade_question(question, 2, None) == (True, 2, None)
    assert quiz_service.grade_question(question, 1, None) == (False, 1, None)
    assert quiz_service.grade_question(question, None, None) == (False, None, None)


def test_grade_free_text_question():
    question = {"is_mcq": False, "correct_option": None, "correct_answer": "media query"}
    assert quiz_service.grade_question(question, None, "Media Query")[0] is True
    assert quiz_service.grade_question(question, None, "database index")[0] is False
    assert quiz_service.grade_question(question, None, "")[0] is False


def test_split_pool_prefers_validated_bank():
    questions = [
        {"id": 1, "source": "manual"},
        {"id": 2, "source": "manual"},
        {"id": 3, "source": "manual"},
        {"id": 4, "source": "template"},
        {"id": 5, "source": "template"},
    ]
    pool = quiz_service._split_pool(questions, 4)
    assert [q["id"] for q in pool] == [1, 2, 3, 4]


def test_split_pool_caps_at_target():
    questions = [{"id": index, "source": "manual"} for index in range(1, 8)]
    assert len(quiz_service._split_pool(questions, 5)) == 5


def test_answer_and_correct_display():
    question = {
        "is_mcq": True,
        "options_list": ["A", "B", "C", "D"],
        "correct_option": 2,
    }
    assert quiz_service.answer_display(question, 1, None) == "B"
    assert quiz_service.answer_display(question, None, None) == "Not answered"
    assert quiz_service.correct_display(question) == "C"


def _catalogue() -> list[dict]:
    return [
        {"id": 1, "name": "Python", "category": "programming"},
        {"id": 2, "name": "Java", "category": "programming"},
        {"id": 3, "name": "JavaScript", "category": "programming"},
        {"id": 4, "name": "Flask", "category": "framework"},
        {"id": 5, "name": "Django", "category": "framework"},
        {"id": 6, "name": "React", "category": "framework"},
        {"id": 7, "name": "SQL", "category": "database"},
        {"id": 8, "name": "MySQL", "category": "database"},
        {"id": 9, "name": "MongoDB", "category": "database"},
        {"id": 10, "name": "Docker", "category": "tool"},
        {"id": 11, "name": "Git", "category": "tool"},
        {"id": 12, "name": "Linux", "category": "tool"},
    ]


def test_template_generation_is_valid_and_unique():
    catalogue = _catalogue()
    for skill in catalogue:
        questions = quiz_templates.generate(skill, catalogue)
        assert len(questions) >= 3
        texts = [q["question_text"] for q in questions]
        assert len(texts) == len(set(texts))
        for question in questions:
            assert question["question_type"] == "mcq"
            assert len(question["options"]) == 4
            assert len(set(question["options"])) == 4
            assert 0 <= question["correct_option"] <= 3
            assert question["explanation"].strip()
            assert question["source"] == "template"


def test_template_generation_is_deterministic():
    catalogue = _catalogue()
    for skill in catalogue:
        assert quiz_templates.generate(skill, catalogue) == quiz_templates.generate(
            skill, catalogue
        )


def test_template_generation_without_peers_returns_available_questions():
    solo = [{"id": 1, "name": "Python", "category": "programming"}]
    questions = quiz_templates.generate(solo[0], solo)
    # Category + task questions are always possible; related/odd-one-out need peers.
    assert len(questions) == 2
    for question in questions:
        assert len(question["options"]) == 4
        assert 0 <= question["correct_option"] <= 3


def test_template_generation_rejects_blank_name():
    assert quiz_templates.generate({"id": 1, "name": "  "}, _catalogue()) == []


def test_level_caps_are_configured():
    assert quiz_service.TEMPLATE_LEVEL_CAP == 3.0
    assert quiz_service.VALIDATED_LEVEL_CAP == 5.0
