"""
A3 - Fusion of self, resume and quiz evidence.

The fused level is:

    current = sum(w_s * level_s) / sum(w_s)   over the evidence sources present

with default weights self 0.30, resume 0.30, quiz 0.40. The properties tested
here are the ones a defensible scoring rule must have:

* weights sum to 1 for every subset of available sources
* the fused value is a weighted average (matches an independent reference)
* the fused value stays inside [min source, max source]
* increasing one source never lowers the fused value
* equal sources stay unchanged (idempotence)
* invalid values are clamped, never propagated

Run:
    .\\.venv\\Scripts\\python.exe evaluation/a3_fusion_consistency.py
"""

from __future__ import annotations

import math
import random
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config  # noqa: E402
from evaluation.common import heading, section, summary  # noqa: E402
from services import skill_service  # noqa: E402

SOURCES = ("self", "resume", "quiz")
VALUES = {"self": 1.0, "resume": 2.0, "quiz": 4.0}


def clamp(value: float) -> float:
    return max(0.0, min(5.0, float(value)))


def reference(levels: dict[str, float | None]) -> tuple[float, dict[str, float]]:
    present = [key for key in SOURCES if levels.get(key) is not None]
    total = sum(Config.FUSION_WEIGHTS[key] for key in present)
    if not present or total <= 0:
        return 0.0, {}
    weights = {key: Config.FUSION_WEIGHTS[key] / total for key in present}
    fused = sum(weights[key] * clamp(levels[key]) for key in weights)  # type: ignore[arg-type]
    return round(fused, 1), weights


def call_fuse(levels: dict[str, float | None]) -> tuple[float, dict[str, float]]:
    """Call the three-argument function positionally ('self' is a keyword)."""
    return skill_service.fuse_levels(levels["self"], levels["resume"], levels["quiz"])


def main() -> int:
    failures: list[str] = []
    checks = 0

    heading("A3 - Evidence fusion consistency")
    print("Configured weights:")
    for key in SOURCES:
        print(f"  {key:<7} {Config.FUSION_WEIGHTS[key]:.2f}")

    section("Weights for every evidence subset")
    for size in range(0, 4):
        for subset in combinations(SOURCES, size):
            levels = {key: (VALUES[key] if key in subset else None) for key in SOURCES}
            actual_fused, actual_weights = call_fuse(levels)
            expected_fused, expected_weights = reference(levels)
            weight_sum = sum(actual_weights.values())
            keys_match = set(actual_weights) == set(subset)
            fused_match = math.isclose(actual_fused, expected_fused, abs_tol=1e-9)
            passed = (
                keys_match
                and fused_match
                and (abs(weight_sum - 1.0) < 1e-6 if subset else not actual_weights)
            )
            checks += 1
            label = "+".join(subset) if subset else "none"
            print(
                f"{'PASS' if passed else 'FAIL'}  {label:<22} "
                f"weights={ {k: round(v, 4) for k, v in actual_weights.items()} } "
                f"fused={actual_fused:.1f}"
            )
            if not passed:
                failures.append(
                    f"subset {label}: weights={actual_weights}, fused={actual_fused}, "
                    f"expected weights={expected_weights}, fused={expected_fused}"
                )

    section("Randomised weighted-average property (1000 cases)")
    rng = random.Random(20261106)
    max_error = 0.0
    out_of_bounds = 0
    monotonic_failures = 0
    missing_weight_failures = 0

    for _ in range(1000):
        raw: dict[str, float | None] = {}
        for key in SOURCES:
            raw[key] = None if rng.random() < 0.30 else rng.uniform(-2.0, 7.0)

        fused, weights = call_fuse(raw)
        expected_fused, _ = reference(raw)
        max_error = max(max_error, abs(fused - expected_fused))
        if abs(fused - expected_fused) > 0.011:
            failures.append(f"weighted-average mismatch: {raw} -> {fused} vs {expected_fused}")

        present = [clamp(raw[key]) for key in SOURCES if raw[key] is not None]
        if present:
            if abs(sum(weights.values()) - 1.0) > 1e-6:
                missing_weight_failures += 1
            if not (min(present) - 0.051 <= fused <= max(present) + 0.051):
                out_of_bounds += 1
        elif weights or fused != 0.0:
            failures.append(f"empty evidence should return (0.0, {{}}), got ({fused}, {weights})")

        # Increasing one present source must not lower the fused value.
        base = dict(raw)
        for key in SOURCES:
            if base[key] is None:
                continue
            bumped = dict(base)
            bumped[key] = clamp(base[key]) + 0.5  # type: ignore[arg-type]
            new_fused, _ = call_fuse(bumped)
            if new_fused < fused - 1e-9:
                monotonic_failures += 1

    checks += 1
    print(f"{'PASS' if max_error <= 0.011 else 'FAIL'}  max |actual - reference| = {max_error:.6f}")
    if max_error > 0.011:
        failures.append(f"weighted-average error too large: {max_error}")

    checks += 1
    print(f"{'PASS' if missing_weight_failures == 0 else 'FAIL'}  weights sum to 1 in every non-empty case "
          f"({missing_weight_failures} failures)")
    if missing_weight_failures:
        failures.append(f"{missing_weight_failures} cases where weights did not sum to 1")

    checks += 1
    print(f"{'PASS' if out_of_bounds == 0 else 'FAIL'}  fused value stays within source bounds "
          f"({out_of_bounds} violations)")
    if out_of_bounds:
        failures.append(f"{out_of_bounds} fused values outside the source range")

    checks += 1
    print(f"{'PASS' if monotonic_failures == 0 else 'FAIL'}  increasing a source never lowers fusion "
          f"({monotonic_failures} violations)")
    if monotonic_failures:
        failures.append(f"{monotonic_failures} monotonicity violations")

    section("Idempotence and invalid input")
    for value in (0.0, 1.5, 2.5, 5.0):
        fused, weights = skill_service.fuse_levels(value, value, value)
        passed = fused == value and abs(sum(weights.values()) - 1.0) < 1e-6
        checks += 1
        print(f"{'PASS' if passed else 'FAIL'}  all sources = {value:.1f} -> fused {fused:.1f}")
        if not passed:
            failures.append(f"idempotence failed for {value}: {fused}")

    fused, weights = skill_service.fuse_levels(None, None, None)
    checks += 1
    print(f"{'PASS' if (fused, weights) == (0.0, {}) else 'FAIL'}  no evidence -> (0.0, {{}})")
    if (fused, weights) != (0.0, {}):
        failures.append(f"no evidence returned ({fused}, {weights})")

    fused, weights = skill_service.fuse_levels(-3, 9, "2.5")
    expected_fused, _ = reference({"self": 0.0, "resume": 5.0, "quiz": 2.5})
    passed = fused == expected_fused and set(weights) == set(SOURCES)
    checks += 1
    print(f"{'PASS' if passed else 'FAIL'}  out-of-range values clamp -> fused {fused:.1f} "
          f"(expected {expected_fused:.1f})")
    if not passed:
        failures.append(f"clamping failed: {fused} vs {expected_fused}")

    fused, weights = skill_service.fuse_levels(None, None, "abc")
    checks += 1
    print(f"{'PASS' if (fused, weights) == (0.0, {}) else 'FAIL'}  junk value is treated as missing")
    if (fused, weights) != (0.0, {}):
        failures.append(f"junk value produced ({fused}, {weights})")

    section("Ablation: same evidence under different source sets")
    print(f"{'self':>5} {'resume':>7} {'quiz':>5} -> {'fused':>5}  weights")
    for self_level, resume_level, quiz_level in [
        (2.0, None, None),
        (None, 3.0, None),
        (None, None, 1.0),
        (2.0, 3.0, None),
        (2.0, None, 1.0),
        (None, 3.0, 1.0),
        (2.0, 3.0, 1.0),
    ]:
        fused, weights = skill_service.fuse_levels(self_level, resume_level, quiz_level)
        print(
            f"{str(self_level or '-'):>5} {str(resume_level or '-'):>7} "
            f"{str(quiz_level or '-'):>5} -> {fused:>5.1f}  "
            f"{ {k: round(v, 3) for k, v in weights.items()} }"
        )

    return summary(failures, checks)


if __name__ == "__main__":
    raise SystemExit(main())
