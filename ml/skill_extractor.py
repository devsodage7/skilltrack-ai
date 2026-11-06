"""
SkillTrack AI - resume skill extraction (algorithm A1).

Pipeline
--------
    PDF text -> normalise -> split into sections
             -> exact alias matching (word-boundary safe)
             -> fuzzy fallback for typos (rapidfuzz, cutoff 90)
             -> evidence scoring -> level 0-5 per skill

Why not "just count keywords"?
-----------------------------
A keyword that appears once in a skills list is weaker evidence than the same
keyword used inside two project descriptions. The scoring below rewards
repetition, section diversity, project usage and proficiency words, and
penalises a single beginner-style list mention. The exact numbers are
documented in the report and can be tuned in one place.

No Flask, no SQL: the function receives the skill catalogue as plain dicts.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Sequence

from config import Config
from ml.skill_aliases import (
    PROFICIENCY_WORDS,
    WEAKNESS_WORDS,
    aliases_for,
)
from ml.text_utils import normalise, skill_pattern, snippet_around, split_sections, word_count

try:  # rapidfuzz is optional at import time
    from rapidfuzz import fuzz, process as fuzz_process
except Exception:  # pragma: no cover - dependency missing
    fuzz = None
    fuzz_process = None

FUZZY_MIN_TOKEN = 6
FUZZY_MIN_ALIAS = 6


# ---------------------------------------------------------------------
# Span helpers
# ---------------------------------------------------------------------
def _merge_spans(spans: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping spans so 'react' + 'react.js' counts once."""
    ordered = sorted(set(spans))
    merged: list[tuple[int, int]] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _word_patterns(words: Sequence[str]) -> list[re.Pattern]:
    """Word-boundary patterns so 'basic' never matches 'databases'."""
    return [re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE) for word in words]


_PROFICIENCY_PATTERNS = _word_patterns(PROFICIENCY_WORDS)
_WEAKNESS_PATTERNS = _word_patterns(WEAKNESS_WORDS)


def _context_hits(
    block: str,
    span: tuple[int, int],
    patterns: Sequence["re.Pattern"],
    width: int = 55,
) -> int:
    start = max(0, span[0] - width)
    end = min(len(block), span[1] + width)
    window = block[start:end]
    return sum(1 for pattern in patterns if pattern.search(window))


def _score_level(
    mentions: int,
    section_count: int,
    project_hits: int,
    proficiency_hits: int,
    weakness_hits: int,
    listed_only: bool,
) -> float:
    """Map evidence volume to a 0-5 level. Deterministic and explainable."""
    if mentions <= 0:
        return 0.0

    if mentions == 1:
        base = 1.5
    elif mentions <= 3:
        base = 2.0
    elif mentions <= 6:
        base = 2.5
    else:
        base = 3.0

    score = base
    if section_count >= 2:
        score += 0.5
    if project_hits >= 1:
        score += 0.5
    if proficiency_hits >= 1:
        score += 0.5
    if weakness_hits >= 1:
        score -= 0.5
    if listed_only:
        score -= 0.5

    return round(min(5.0, max(1.0, score)), 1)


# ---------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------
def extract_skills(
    text: str,
    skills: Sequence[dict],
    requirements: Sequence[dict] | None = None,
) -> dict:
    """
    Extract skill evidence from resume text.

    Parameters
    ----------
    text         : raw text extracted from the PDF
    skills       : [{"id", "name", "category"}] from the skills table
    requirements : optional career_skills rows used to compute a match score

    Returns a dict with `detected`, `not_detected`, `match_score`, `stats`.
    """
    clean = normalise(text)
    blocks = split_sections(clean)
    tokens = re.findall(r"[A-Za-z]+", clean)

    detected: list[dict] = []
    not_detected: list[dict] = []
    detected_names: set[str] = set()

    for skill in skills:
        name = str(skill.get("name") or "").strip()
        if not name:
            continue
        patterns = [skill_pattern(alias) for alias in aliases_for(name)]

        spans: list[tuple[int, int]] = []
        sections: set[str] = set()
        snippets: list[str] = []
        proficiency_hits = 0
        weakness_hits = 0
        project_hits = 0

        for label, block in blocks:
            local: list[tuple[int, int]] = []
            for pattern in patterns:
                local.extend((m.start(), m.end()) for m in pattern.finditer(block))

            merged = _merge_spans(local)
            if not merged:
                continue

            sections.add(label)
            spans.extend(merged)
            if label in {"projects", "experience"}:
                project_hits += len(merged)

            for span in merged:
                proficiency_hits += _context_hits(block, span, _PROFICIENCY_PATTERNS)
                weakness_hits += _context_hits(block, span, _WEAKNESS_PATTERNS)

            if len(snippets) < 2:
                for pattern in patterns:
                    match = pattern.search(block)
                    if match:
                        snippets.append(snippet_around(block, match))
                        break

        mentions = len(spans)
        level = 0.0
        signals: list[str] = []

        if mentions:
            listed_only = sections <= {"skills"}
            level = _score_level(
                mentions=mentions,
                section_count=len(sections),
                project_hits=project_hits,
                proficiency_hits=proficiency_hits,
                weakness_hits=weakness_hits,
                listed_only=listed_only,
            )
            signals.append(f"{mentions} mention(s)")
            if len(sections) >= 2:
                signals.append(f"{len(sections)} sections")
            if project_hits:
                signals.append("used in projects/experience")
            if proficiency_hits:
                signals.append("proficiency wording")
            if weakness_hits:
                signals.append("beginner wording")
            if listed_only:
                signals.append("skills list only")

        entry = {
            "skill_id": int(skill["id"]),
            "name": name,
            "category": skill.get("category") or "concept",
            "mentions": mentions,
            "level": level,
            "sections": sorted(sections),
            "signals": signals,
            "snippets": snippets,
        }

        if mentions:
            detected.append(entry)
            detected_names.add(name.lower())
        else:
            not_detected.append(entry)

    fuzzy_hits = _fuzzy_pass(clean, skills, detected_names, tokens, detected)

    detected.sort(key=lambda row: (-row["level"], -row["mentions"], row["name"]))
    match_score, match_detail = _match_score(detected, requirements or [])

    return {
        "detected": detected,
        "not_detected": sorted(not_detected, key=lambda row: row["name"]),
        "fuzzy_hits": fuzzy_hits,
        "match_score": match_score,
        "match_detail": match_detail,
        "stats": {
            "chars": len(clean),
            "words": word_count(clean),
            "sections": [label for label, _ in blocks],
            "skills_detected": len(detected),
            "skills_considered": len(skills),
        },
    }


def _fuzzy_pass(
    clean: str,
    skills: Sequence[dict],
    detected_names: set[str],
    tokens: Sequence[str],
    detected: list[dict],
) -> list[dict]:
    """
    Catch typos ("pytorch" -> "pytoch", "tensorflow" -> "tensor flow").

    Only alphabetic aliases of at least 6 characters are used, with a high
    cutoff, so short words ("sql", "git", "r") can never fuzzy-match by
    accident. At most one fuzzy hit per skill is recorded.
    """
    if fuzz is None or fuzz_process is None or not tokens:
        return []

    choices: dict[str, str] = {}
    skill_by_name = {str(s["name"]).lower(): s for s in skills}
    for skill in skills:
        if str(skill["name"]).lower() in detected_names:
            continue
        for alias in aliases_for(str(skill["name"])):
            if len(alias) >= FUZZY_MIN_ALIAS and alias.isalpha():
                choices.setdefault(alias, str(skill["name"]))

    if not choices:
        return []

    unique_tokens = {t for t in tokens if len(t) >= FUZZY_MIN_TOKEN and t.isalpha()}
    hits: list[dict] = []
    used: set[str] = set()

    for token in unique_tokens:
        result = fuzz_process.extractOne(
            token,
            list(choices.keys()),
            scorer=fuzz.WRatio,
            score_cutoff=90,
        )
        if not result:
            continue
        alias, score = result[0], float(result[1])
        name = choices[alias]
        if name.lower() in used:
            continue

        skill = skill_by_name.get(name.lower())
        if not skill:
            continue

        used.add(name.lower())
        level = 1.5
        hits.append(
            {
                "skill_id": int(skill["id"]),
                "name": name,
                "matched_token": token,
                "matched_alias": alias,
                "score": round(score, 1),
                "level": level,
            }
        )
        detected.append(
            {
                "skill_id": int(skill["id"]),
                "name": name,
                "category": skill.get("category") or "concept",
                "mentions": 1,
                "level": level,
                "sections": ["fuzzy"],
                "signals": [f"fuzzy match '{token}' ~ '{alias}' ({score:.0f})"],
                "snippets": [],
            }
        )

    return hits


def _match_score(detected: Sequence[dict], requirements: Sequence[dict]) -> tuple[float | None, dict]:
    """
    Resume-only weighted match against a career requirement matrix.

    Uses the same weighted formula as readiness, but with resume evidence
    only (self ratings and quiz scores are deliberately excluded here).
    """
    if not requirements:
        return None, {"counted": 0, "reason": "No career requirements supplied."}

    levels = {int(row["skill_id"]): float(row["level"]) for row in detected}
    numerator = 0.0
    denominator = 0.0
    counted = 0

    for req in requirements:
        try:
            weight = max(0.0, float(req.get("weight") or 0))
            required = max(0.0, min(5.0, float(req.get("required_level") or 0)))
            skill_id = int(req["skill_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if weight <= 0 or required <= 0:
            continue

        current = max(0.0, min(5.0, levels.get(skill_id, 0.0)))
        numerator += weight * min(current, required)
        denominator += weight * required
        counted += 1

    if denominator <= 1e-9:
        return None, {"counted": 0, "reason": "Zero weighted requirements."}

    return round(numerator / denominator * 100.0, 2), {
        "counted": counted,
        "matched": len(levels),
        "threshold": Config.FUZZY_MATCH_THRESHOLD,
    }
