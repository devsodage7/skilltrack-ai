"""Career recommendation service - orchestration only."""

from __future__ import annotations

from ml import career_matcher
from models import career_model, student_model
from services import gap_service


def recommend(student_id: int, limit: int | None = None) -> list[dict]:
    """Rank every active career for one student."""
    student = student_model.get_by_id(student_id)
    analyses = gap_service.analyze_all(student_id)
    careers = career_model.list_careers()
    ranked = career_matcher.rank_careers(
        analyses, career_matcher.build_student_text(student), careers
    )
    return ranked[:limit] if limit else ranked


def best_matches(student_id: int, limit: int = 3) -> list[dict]:
    """Small list for the dashboard."""
    return recommend(student_id, limit=limit)


def analysis_for(student_id: int, career_id: int) -> dict:
    """Readiness detail for a single career (used by the compare view)."""
    return gap_service.analyze(student_id, career_id)
