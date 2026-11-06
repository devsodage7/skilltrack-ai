"""
SkillTrack AI - career recommendation (algorithm A5).

Hybrid ranker
-------------
    score(career) = w_gap * readiness(career) + w_text * 100 * cosine(student_text, career_text)

* readiness comes from the weighted gap engine (evidence driven)
* text similarity compares the student's stated interests/branch with the
  career name + description + keywords (TF-IDF, cosine)
* weights live in Config (0.60 / 0.40) and are renormalised if one side is
  missing, so a student with no interests is still ranked by readiness and
  a student with no skills is still ranked by interests.

Every recommendation carries human-readable reasons so the result is not a
black box.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Sequence

from config import Config

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover - sklearn missing
    TfidfVectorizer = None
    cosine_similarity = None

_TOKEN_RE = re.compile(r"[a-z][a-z+#.]{1,}")

_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "are", "our", "this", "that",
    "from", "into", "will", "can", "have", "has", "who", "how", "what", "all",
    "not", "but", "use", "using", "build", "builds", "work", "works", "role",
    "job", "career", "engineer", "engineering", "developer", "analyst",
}


def _tokens(text: str | None) -> set[str]:
    return {
        token for token in _TOKEN_RE.findall((text or "").lower())
        if token not in _STOPWORDS and len(token) > 1
    }


def _career_document(career: dict) -> str:
    return " ".join(
        str(career.get(key) or "")
        for key in ("name", "description", "keywords")
    ).strip()


def text_scores(student_text: str, careers: Sequence[dict]) -> dict[int, dict]:
    """
    Interest relevance for every career.

    Metric: TF-IDF weighted query coverage.

        coverage(career) = sum(idf(t) for t in query_tokens AND career_tokens)
                           ---------------------------------------------------
                                   sum(idf(t) for t in query_tokens)

    A plain cosine on a short query against a long description is always tiny
    (0.02-0.06), which makes the 40% text weight almost meaningless. Coverage
    answers the question the UI actually asks: "how much of what you said is
    relevant to this role?", and rare terms (kaggle, pytorch) weigh more than
    common ones (data, model). Raw cosine is still returned for transparency
    and used as a tie-breaker.

    Returns {career_id: {"score": 0-1, "cosine": 0-1, "matched": [tokens]}}.
    """
    documents = [_career_document(career) for career in careers]
    ids = [int(career["id"]) for career in careers]
    empty = {
        career_id: {"score": 0.0, "cosine": 0.0, "matched": []}
        for career_id in ids
    }

    query = (student_text or "").strip()
    if not query or not careers:
        return empty

    if TfidfVectorizer is None or cosine_similarity is None:
        return _fallback_scores(query, ids, documents)

    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 1),
            sublinear_tf=True,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z+#.]{1,}\b",
        )
        matrix = vectorizer.fit_transform(documents + [query])
        feature_names = list(vectorizer.get_feature_names_out())
        idf = {name: float(value) for name, value in zip(feature_names, vectorizer.idf_)}
        analyzer = vectorizer.build_analyzer()
        query_tokens = set(analyzer(query))
    except ValueError:
        return _fallback_scores(query, ids, documents)

    if not query_tokens:
        return empty

    # Unknown tokens (not in the tiny corpus) get the highest idf so that a
    # very specific interest is not silently ignored.
    default_idf = max(idf.values()) if idf else 1.0
    weight = lambda token: idf.get(token, default_idf)  # noqa: E731

    denominator = sum(weight(token) for token in query_tokens)
    cosine_values = cosine_similarity(matrix[-1], matrix[:-1]).ravel()

    result: dict[int, dict] = {}
    for index, (career_id, document) in enumerate(zip(ids, documents)):
        try:
            career_tokens = set(analyzer(document))
        except ValueError:
            career_tokens = _tokens(document)

        shared = query_tokens & career_tokens
        numerator = sum(weight(token) for token in shared)
        coverage = (numerator / denominator) if denominator > 0 else 0.0

        result[career_id] = {
            "score": round(max(0.0, min(1.0, coverage)), 4),
            "cosine": round(max(0.0, min(1.0, float(cosine_values[index]))), 4),
            "matched": sorted(shared)[:8],
        }
    return result


def _fallback_scores(query: str, ids: Sequence[int], documents: Sequence[str]) -> dict[int, dict]:
    """Unweighted overlap when scikit-learn is unavailable."""
    query_tokens = _tokens(query)
    result: dict[int, dict] = {}
    for career_id, document in zip(ids, documents):
        career_tokens = _tokens(document)
        shared = query_tokens & career_tokens
        score = len(shared) / len(query_tokens) if query_tokens else 0.0
        result[career_id] = {
            "score": round(max(0.0, min(1.0, score)), 4),
            "cosine": 0.0,
            "matched": sorted(shared)[:8],
        }
    return result


def blend_weights(has_readiness: bool, has_text: bool) -> tuple[float, float]:
    """Renormalise the blend when one signal is absent."""
    gap_w = float(Config.RECOMMEND_WEIGHT_GAP)
    text_w = float(Config.RECOMMEND_WEIGHT_TEXT)
    if not has_readiness:
        gap_w = 0.0
    if not has_text:
        text_w = 0.0
    total = gap_w + text_w
    if total <= 0:
        return 0.0, 0.0
    return gap_w / total, text_w / total


def fit_label(score: float) -> str:
    if score >= 72:
        return "Strong fit"
    if score >= 55:
        return "Good fit"
    if score >= 38:
        return "Possible fit"
    return "Stretch goal"


def rank_careers(
    analyses: Sequence[dict],
    student_text: str,
    careers: Sequence[dict],
) -> list[dict]:
    """
    Rank careers for one student.

    `analyses` is the output of gap_service.analyze_all (readiness per career).
    """
    sims = text_scores(student_text, careers)
    has_any_readiness = any(float(a.get("readiness") or 0) > 0 for a in analyses)
    has_any_text = any(item["score"] > 0 for item in sims.values())

    ranked: list[dict] = []
    for analysis in analyses:
        career = analysis.get("career") or {}
        career_id = int(career.get("id") or 0)
        readiness = float(analysis.get("readiness") or 0.0)
        text = sims.get(career_id, {"score": 0.0, "matched": []})

        gap_w, text_w = blend_weights(has_any_readiness, has_any_text)
        interest_pct = min(100.0, text["score"] * 100.0 * float(Config.RECOMMEND_TEXT_GAIN))
        final = gap_w * readiness + text_w * interest_pct

        reasons: list[str] = []
        if readiness > 0:
            reasons.append(f"{readiness:.0f}% of the weighted requirements are covered")
        else:
            reasons.append("No evidence recorded for this path yet")
        if text["matched"]:
            reasons.append("Interest overlap: " + ", ".join(text["matched"][:4]))
        elif has_any_text:
            reasons.append("No overlap with your stated interests")
        top_gaps = analysis.get("top_gaps", [])[:3]
        if top_gaps:
            reasons.append("Next gaps: " + ", ".join(g["skill_name"] for g in top_gaps))

        ranked.append(
            {
                "career": career,
                "career_id": career_id,
                "readiness": round(readiness, 2),
                "readiness_band": analysis.get("band"),
                "text_similarity": round(interest_pct, 2),
                "text_coverage": round(text["score"] * 100.0, 2),
                "text_cosine": round(text.get("cosine", 0.0) * 100.0, 2),
                "matched_keywords": text["matched"],
                "final_score": round(max(0.0, min(100.0, final)), 2),
                "fit": fit_label(final),
                "reasons": reasons,
                "top_gaps": top_gaps,
                "counts": analysis.get("counts", {}),
                "blend": {"readiness": round(gap_w, 2), "text": round(text_w, 2)},
            }
        )

    ranked.sort(key=lambda row: (-row["final_score"], -row["readiness"], row["career_id"]))
    return ranked


def build_student_text(student: dict | None) -> str:
    """Concatenate the free-text fields that describe what the student wants."""
    if not student:
        return ""
    parts = [
        student.get("interests") or "",
        student.get("branch") or "",
        student.get("education") or "",
    ]
    return " ".join(part for part in parts if part).strip()


def explain_blend() -> str:
    return (
        f"Final score = {Config.RECOMMEND_WEIGHT_GAP:.0%} x readiness + "
        f"{Config.RECOMMEND_WEIGHT_TEXT:.0%} x interest match. Readiness is the weighted "
        "gap formula; the interest part is TF-IDF weighted coverage of the words you used "
        "in your profile, calibrated so a handful of specific terms counts as a strong match. "
        "If one signal is missing the other takes its full weight."
    )
