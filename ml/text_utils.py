"""Text helpers shared by the resume analyser and the career matcher."""

from __future__ import annotations

import re

_HR = re.compile(r"[ \t]{2,}")

_BULLETS = {
    "\u2022": "-", "\u25cf": "-", "\u25aa": "-", "\u25a0": "-",
    "\u2013": "-", "\u2014": "-", "\u00a0": " ", "\u200b": "",
}


def normalise(text: str | None) -> str:
    """Lowercase, unify bullets/dashes, collapse whitespace, keep newlines."""
    if not text:
        return ""
    value = str(text)
    for source, target in _BULLETS.items():
        value = value.replace(source, target)
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    lines = [_HR.sub(" ", line).strip() for line in value.split("\n")]
    value = "\n".join(lines)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def word_count(text: str | None) -> int:
    return len(re.findall(r"[A-Za-z0-9+#./-]+", text or ""))


def _heading_label(line: str, patterns) -> str | None:
    """Return a section label when the line looks like a heading."""
    clean = line.strip().strip(":").strip()
    if not clean or len(clean) > 48:
        return None
    words = re.findall(r"[a-z/&]+", clean.lower())
    if not words or len(words) > 6:
        return None

    lowered = clean.lower()
    for label, keywords in patterns:
        for keyword in keywords:
            if lowered == keyword or lowered.startswith(keyword + " ") or lowered.endswith(" " + keyword):
                return label
            # "TECHNICAL SKILLS" / "Work Experience:" style
            if keyword in lowered and len(words) <= 4:
                return label
    return None


def split_sections(text: str) -> list[tuple[str, str]]:
    """
    Split a CV into labelled blocks.

    Returns [("general", "..."), ("skills", "..."), ...]. Unknown headings
    keep the previous label, which is safer than dropping the text.
    """
    from ml.skill_aliases import SECTION_PATTERNS

    blocks: list[tuple[str, list[str]]] = []
    current_label = "general"
    current_lines: list[str] = []

    for line in normalise(text).split("\n"):
        label = _heading_label(line, SECTION_PATTERNS)
        if label:
            if current_lines:
                blocks.append((current_label, current_lines))
            current_label = label
            current_lines = []
            continue
        current_lines.append(line)

    if current_lines:
        blocks.append((current_label, current_lines))

    if not blocks:
        return [("general", normalise(text))]

    return [(label, "\n".join(lines).strip()) for label, lines in blocks if "\n".join(lines).strip()]


def snippet_around(text: str, match: re.Match, width: int = 72) -> str:
    """One-line context window around a regex match, ellipsised."""
    start = max(0, match.start() - width)
    end = min(len(text), match.end() + width)
    piece = " ".join(text[start:end].split())
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{piece}{suffix}"


def skill_pattern(alias: str) -> re.Pattern:
    """
    Word-boundary safe pattern for one alias.

    Boundaries treat '+' and '#' as word characters so "c++" does not match
    inside "c++11" style noise, and "java" never matches "javascript".
    """
    escaped = re.escape(alias.strip().lower())
    escaped = escaped.replace(r"\ ", r"[\s\-]+")
    return re.compile(rf"(?<![a-z0-9+#]){escaped}(?![a-z0-9+#])", re.IGNORECASE)
