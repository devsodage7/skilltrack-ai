"""Unit tests for resume skill extraction (algorithm A1)."""

from __future__ import annotations

from ml import skill_extractor

SKILLS = [
    {"id": 1, "name": "Python", "category": "programming"},
    {"id": 2, "name": "Java", "category": "programming"},
    {"id": 3, "name": "JavaScript", "category": "programming"},
    {"id": 4, "name": "Excel", "category": "tool"},
    {"id": 5, "name": "PyTorch", "category": "tool"},
    {"id": 6, "name": "Computer Vision", "category": "concept"},
    {"id": 7, "name": "Statistics", "category": "concept"},
]


def names(result: dict) -> set[str]:
    return {row["name"] for row in result["detected"]}


def test_exact_aliases_are_detected():
    result = skill_extractor.extract_skills(
        "Skills\nPython, JavaScript, Excel and PyTorch.", SKILLS
    )
    assert names(result) == {"Python", "JavaScript", "Excel", "PyTorch"}


def test_word_boundaries_prevent_false_positives():
    result = skill_extractor.extract_skills(
        "Senior JavaScript developer. Excellent communication. Restaurant team lead.",
        SKILLS,
    )
    assert names(result) == {"JavaScript"}


def test_java_is_not_matched_inside_javascript():
    result = skill_extractor.extract_skills("Built JavaScript applications.", SKILLS)
    assert "Java" not in names(result)


def test_fuzzy_matching_recovers_a_typo():
    result = skill_extractor.extract_skills(
        "Projects\nTrained a model in pytoch.", SKILLS
    )
    assert "PyTorch" in names(result)
    hit = next(row for row in result["detected"] if row["name"] == "PyTorch")
    assert hit["sections"] == ["fuzzy"]
    assert result["fuzzy_hits"]


def test_skills_list_only_scores_lower_than_project_usage():
    listed = skill_extractor.extract_skills("Skills\nPython", SKILLS)
    projects = skill_extractor.extract_skills(
        "Projects\nExpert Python developer. Built Python APIs. Python automation.",
        SKILLS,
    )
    listed_level = next(row["level"] for row in listed["detected"] if row["name"] == "Python")
    project_level = next(row["level"] for row in projects["detected"] if row["name"] == "Python")
    assert listed_level == 1.0
    assert project_level > listed_level


def test_beginner_wording_lowers_the_level():
    weak = skill_extractor.extract_skills("I know basic Python.", SKILLS)
    level = next(row["level"] for row in weak["detected"] if row["name"] == "Python")
    assert level == 1.0


def test_match_score_uses_career_requirements():
    requirements = [
        {"skill_id": 1, "weight": 2, "required_level": 5},
        {"skill_id": 4, "weight": 1, "required_level": 3},
    ]
    result = skill_extractor.extract_skills("Skills\nPython, Excel", SKILLS, requirements)
    assert result["match_score"] is not None
    assert 0 <= result["match_score"] <= 100
    assert result["match_detail"]["counted"] == 2


def test_empty_text_returns_no_detections():
    result = skill_extractor.extract_skills("", SKILLS)
    assert result["detected"] == []
    assert result["stats"]["skills_detected"] == 0
