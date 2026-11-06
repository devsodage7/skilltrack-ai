"""
Run every SkillTrack AI evaluation script and print a final summary.

    .\\.venv\\Scripts\\python.exe evaluation/run_all.py
    .\\.venv\\Scripts\\python.exe evaluation/run_all.py a1 a4

Each script is independent and exits non-zero only when a structural invariant
fails. Measured metrics (precision, recall, top-1 accuracy, ...) are printed by
the individual scripts and are not hidden by this runner.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent

SCRIPTS = [
    ("A1", "a1_resume_extraction.py", "Resume skill extraction"),
    ("A2", "a2_quiz_mapping.py", "Quiz mapping and grading"),
    ("A3", "a3_fusion_consistency.py", "Evidence fusion"),
    ("A4", "a4_gap_readiness.py", "Gap and readiness formula"),
    ("A5", "a5_recommender.py", "Career recommendation"),
    ("A6", "a6_roadmap.py", "Roadmap ordering and scheduling"),
    ("A7", "a7_question_validity.py", "Question validity"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SkillTrack AI evaluations")
    parser.add_argument(
        "only",
        nargs="*",
        help="Optional prefixes to run (e.g. a1 a4). Default: all.",
    )
    args = parser.parse_args()

    selected = [
        item
        for item in SCRIPTS
        if not args.only or any(item[1].startswith(prefix) for prefix in args.only)
    ]
    if not selected:
        print(f"No script matches {args.only}")
        return 2

    results: list[tuple[str, str, int, float]] = []
    for code, filename, label in selected:
        print()
        print("#" * 72)
        print(f"# {code}: {label}")
        print("#" * 72)
        started = time.perf_counter()
        completed = subprocess.run(
            [sys.executable, str(EVAL_DIR / filename)],
            cwd=str(ROOT),
        )
        elapsed = time.perf_counter() - started
        results.append((code, label, completed.returncode, elapsed))

    print()
    print("=" * 72)
    print("Evaluation summary")
    print("=" * 72)
    print(f"{'code':<6} {'result':<8} {'time':>8}  module")
    failures = 0
    for code, label, returncode, elapsed in results:
        status = "OK" if returncode == 0 else "FAIL"
        failures += int(returncode != 0)
        print(f"{code:<6} {status:<8} {elapsed:>7.1f}s  {label}")

    print()
    if failures:
        print(f"{failures} of {len(results)} evaluation script(s) reported a failed invariant.")
        return 1
    print(f"All {len(results)} evaluation scripts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
