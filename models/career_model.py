"""Career repository - SQL only."""

from __future__ import annotations

from models.db import query_all, query_one, scalar


def list_careers(active_only: bool = True) -> list[dict]:
    if active_only:
        return query_all(
            "SELECT id, name, slug, description, keywords FROM careers "
            "WHERE is_active = 1 ORDER BY name"
        )
    return query_all(
        "SELECT id, name, slug, description, keywords, is_active "
        "FROM careers ORDER BY name"
    )


def get_career(career_id: int) -> dict | None:
    return query_one(
        "SELECT id, name, slug, description, keywords, is_active "
        "FROM careers WHERE id = %s",
        (career_id,),
    )


def get_by_slug(slug: str) -> dict | None:
    return query_one(
        "SELECT id, name, slug, description, keywords, is_active "
        "FROM careers WHERE slug = %s",
        (slug,),
    )


def count_careers(active_only: bool = True) -> int:
    if active_only:
        return int(scalar("SELECT COUNT(*) FROM careers WHERE is_active = 1", default=0))
    return int(scalar("SELECT COUNT(*) FROM careers", default=0))


def career_requirements(career_id: int) -> list[dict]:
    """Weighted requirement matrix for one career, joined with skill names."""
    return query_all(
        """
        SELECT cs.id, cs.skill_id, cs.required_level, cs.weight,
               cs.prerequisite_skill_id,
               s.name AS skill_name, s.category
          FROM career_skills cs
          JOIN skills s ON s.id = cs.skill_id
         WHERE cs.career_id = %s
         ORDER BY cs.weight DESC, s.name
        """,
        (career_id,),
    )


def all_requirements() -> list[dict]:
    """Every requirement row - used once per request by the recommender."""
    return query_all(
        """
        SELECT cs.career_id, cs.skill_id, cs.required_level, cs.weight,
               cs.prerequisite_skill_id, s.name AS skill_name
          FROM career_skills cs
          JOIN skills s ON s.id = cs.skill_id
         ORDER BY cs.career_id, cs.weight DESC
        """
    )
