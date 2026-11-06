"""Unit tests for the interest matcher and hybrid blend (algorithm A5)."""

from __future__ import annotations

import pytest

from ml import career_matcher

CAREERS = [
    {
        "id": 1,
        "name": "Python Developer",
        "description": "Backend services and APIs with Python, Flask and Django.",
        "keywords": "python, flask, django, backend, api, rest, sql, docker, linux",
    },
    {
        "id": 2,
        "name": "Data Analyst",
        "description": "Dashboards, spreadsheets, SQL and business reporting.",
        "keywords": "excel, sql, power bi, tableau, dashboard, statistics, data cleaning",
    },
    {
        "id": 3,
        "name": "Cybersecurity Analyst",
        "description": "Monitor networks, SIEM alerts, web security and incident response.",
        "keywords": "networking, siem, splunk, owasp, cryptography, linux, incident response",
    },
]


def test_text_scores_rank_the_obvious_career_first():
    scores = career_matcher.text_scores(
        "I enjoy Flask APIs, backend Python and SQL on Linux.", CAREERS
    )
    ranked = sorted(scores, key=lambda cid: -scores[cid]["score"])
    assert ranked[0] == 1
    assert scores[1]["score"] > scores[2]["score"]


def test_text_scores_are_bounded_and_return_cosine():
    scores = career_matcher.text_scores("python flask", CAREERS)
    for item in scores.values():
        assert 0.0 <= item["score"] <= 1.0
        assert 0.0 <= item["cosine"] <= 1.0
        assert isinstance(item["matched"], list)


def test_empty_query_and_stopwords_return_zero():
    for query in ("", "the and for with you"):
        scores = career_matcher.text_scores(query, CAREERS)
        assert all(item["score"] == 0.0 for item in scores.values())


def test_no_careers_returns_empty_mapping():
    assert career_matcher.text_scores("python", []) == {}


@pytest.mark.parametrize(
    "has_readiness,has_text,expected",
    [
        (True, True, (0.6, 0.4)),
        (True, False, (1.0, 0.0)),
        (False, True, (0.0, 1.0)),
        (False, False, (0.0, 0.0)),
    ],
)
def test_blend_weights_renormalise(has_readiness, has_text, expected):
    assert career_matcher.blend_weights(has_readiness, has_text) == expected


def test_build_student_text_joins_profile_fields():
    text = career_matcher.build_student_text(
        {"interests": "ML", "branch": "AI", "education": "B.Tech"}
    )
    assert text == "ML AI B.Tech"
    assert career_matcher.build_student_text(None) == ""


def test_fit_labels():
    assert career_matcher.fit_label(80) == "Strong fit"
    assert career_matcher.fit_label(60) == "Good fit"
    assert career_matcher.fit_label(40) == "Possible fit"
    assert career_matcher.fit_label(10) == "Stretch goal"


def test_rank_careers_formula_and_order():
    analyses = [
        {
            "career": CAREERS[0],
            "readiness": 60.0,
            "band": "Developing",
            "top_gaps": [],
            "counts": {},
        },
        {
            "career": CAREERS[1],
            "readiness": 20.0,
            "band": "Foundation stage",
            "top_gaps": [],
            "counts": {},
        },
    ]
    ranked = career_matcher.rank_careers(
        analyses, "python flask backend", CAREERS[:2]
    )
    assert len(ranked) == 2
    assert ranked[0]["career_id"] == 1
    for row in ranked:
        expected = (
            row["blend"]["readiness"] * row["readiness"]
            + row["blend"]["text"] * row["text_similarity"]
        )
        assert row["final_score"] == pytest.approx(expected, abs=0.011)
        assert 0.0 <= row["final_score"] <= 100.0
