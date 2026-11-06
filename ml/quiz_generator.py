"""
Quiz generation (algorithm A7).

Two backends, both free and local:

1. `ollama_questions` - optional local LLM through Ollama's REST API.
   It is used only when the server is reachable, and every question is
   structurally validated before it can reach the database.
2. `ml.quiz_templates` - deterministic offline fallback that needs no model
   at all, so the application works on a laptop with nothing installed.

The generator never invents a "correct" answer silently: MCQs must carry
exactly four options, an index in range and a non-empty explanation.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Mapping, Sequence

from config import Config
from ml import quiz_templates

_AVAILABILITY: dict[str, float | bool] = {"checked_at": 0.0, "ok": False}
_AVAILABILITY_TTL = 60.0


def ollama_available() -> bool:
    """Cheap reachability probe, cached for one minute."""
    if not Config.OLLAMA_ENABLED:
        return False
    now = time.time()
    if now - float(_AVAILABILITY["checked_at"]) < _AVAILABILITY_TTL:
        return bool(_AVAILABILITY["ok"])

    ok = False
    try:
        request = urllib.request.Request(f"{Config.OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=1.5) as response:
            ok = 200 <= response.status < 300
    except Exception:  # noqa: BLE001 - offline is the normal case
        ok = False

    _AVAILABILITY["checked_at"] = now
    _AVAILABILITY["ok"] = ok
    return ok


def _prompt(skill: Mapping, count: int, difficulty: str) -> str:
    return (
        "You are writing a short multiple-choice quiz for a B.Tech student.\n"
        f"Skill: {skill.get('name')} (category: {skill.get('category')}).\n"
        f"Difficulty: {difficulty}.\n"
        f"Write exactly {count} questions.\n"
        "Return ONLY a JSON object with this shape:\n"
        '{"questions": [{"question": "...", "options": ["a", "b", "c", "d"], '
        '"correct": 0, "explanation": "..."}]}\n'
        "Rules: 4 options, exactly one correct, correct is the 0-based index, "
        "explanation at most 30 words, no markdown, no extra keys."
    )


def _parse(raw: str) -> list[dict]:
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return []

    if isinstance(payload, dict):
        items = payload.get("questions")
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    cleaned: list[dict] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("question") or "").strip()
        options = item.get("options")
        explanation = str(item.get("explanation") or "").strip()
        try:
            correct = int(item.get("correct"))
        except (TypeError, ValueError):
            continue

        if not text or not isinstance(options, list) or len(options) != 4:
            continue
        options = [str(value).strip() for value in options]
        if any(not value for value in options) or len(set(options)) != 4:
            continue
        if correct < 0 or correct > 3 or not explanation:
            continue

        cleaned.append(
            {
                "question_type": "mcq",
                "difficulty": str(item.get("difficulty") or "beginner").lower(),
                "question_text": text[:2000],
                "options": options,
                "correct_option": correct,
                "correct_answer": None,
                "explanation": explanation[:2000],
                "source": "ollama",
            }
        )
    return cleaned


def ollama_questions(skill: Mapping, count: int, difficulty: str = "intermediate") -> tuple[list[dict], str]:
    """
    Ask the local model for `count` MCQs.

    Returns (questions, note). `note` is a human-readable reason when the
    backend was skipped, so the UI can explain the fallback.
    """
    if count <= 0:
        return [], ""
    if not ollama_available():
        return [], "Ollama is not running, so template questions were used."

    body = json.dumps(
        {
            "model": Config.OLLAMA_MODEL,
            "prompt": _prompt(skill, count, difficulty),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.4},
        }
    ).encode("utf-8")

    try:
        request = urllib.request.Request(
            f"{Config.OLLAMA_BASE_URL}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=min(Config.OLLAMA_TIMEOUT, 12)) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        questions = _parse(str(payload.get("response") or ""))
    except Exception as exc:  # noqa: BLE001 - fall back, never crash the quiz
        return [], f"Ollama request failed ({type(exc).__name__}), template questions were used."

    if not questions:
        return [], "Ollama returned no valid questions, template questions were used."
    return questions[:count], ""


def template_questions(skill: Mapping, all_skills: Sequence[Mapping]) -> list[dict]:
    """Offline fallback questions for one skill."""
    return quiz_templates.generate(skill, all_skills)
