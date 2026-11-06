"""Shared helpers for the SkillTrack AI evaluation scripts.

Every script in this folder is runnable on its own:

    .\\.venv\\Scripts\\python.exe evaluation/a1_resume_extraction.py

They print measurements, not marketing numbers. The scripts use the same
modules as the web application, so a change in the app is reflected here
immediately.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config  # noqa: E402
from models import db  # noqa: E402


def init_db() -> None:
    """Create the MySQL pool once for scripts that read the catalogue."""
    db.init_pool(Config)


def load_skills() -> list[dict]:
    init_db()
    return db.query_all("SELECT id, name, category FROM skills ORDER BY id")


def load_careers() -> list[dict]:
    init_db()
    return db.query_all(
        "SELECT id, name, slug, description, keywords FROM careers "
        "WHERE is_active = 1 ORDER BY id"
    )


def heading(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def section(title: str) -> None:
    print()
    print("-" * 72)
    print(title)
    print("-" * 72)


def summary(failures: list[str], checks: int) -> int:
    """Print a consistent footer and return a process exit code."""
    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)} of {checks} checks failed)")
        for item in failures[:20]:
            print(f"  - {item}")
        return 1
    print(f"RESULT: OK ({checks} checks passed)")
    return 0
