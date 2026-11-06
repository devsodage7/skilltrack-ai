"""
A5 - Career recommendation: interest ranking and hybrid score checks.

Part 1 is a hand-labelled benchmark of 16 interest statements (2 per career).
For each statement the expected career is known. We report top-1 accuracy,
top-3 accuracy and mean reciprocal rank of the TF-IDF interest matcher.

Part 2 verifies the hybrid ranker on real seeded data:
* final score = readiness blend + interest blend, recomputed independently
* blend weights are renormalised when one signal is missing
* results are deterministic and sorted
* readiness-only, text-only and hybrid rankings are shown side by side

The 16 statements are a small synthetic benchmark, not a claim of accuracy on
real students. They exist to catch regressions in the text matcher.

Run:
    .\\.venv\\Scripts\\python.exe evaluation/a5_recommender.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config  # noqa: E402
from evaluation.common import heading, load_careers, section, summary  # noqa: E402
from ml import career_matcher  # noqa: E402
from models import student_model  # noqa: E402
from services import gap_service  # noqa: E402

QUERIES: list[tuple[str, str]] = [
    ("Python Developer", "Python backend development with Flask, Django, REST APIs, pytest and Docker on Linux."),
    ("Python Developer", "I enjoy writing Python automation scripts, SQL queries and clean backend services."),
    ("Data Analyst", "Excel spreadsheets, SQL queries, Power BI dashboards and KPI reporting for business teams."),
    ("Data Analyst", "Data cleaning, statistics, visualization and explaining findings to stakeholders."),
    ("Data Scientist", "Machine learning models with Python, pandas, scikit-learn, statistics and feature engineering."),
    ("Data Scientist", "Statistical regression, classification, cross validation and model evaluation experiments."),
    ("Machine Learning Engineer", "Train deep learning models in PyTorch and TensorFlow, then deploy them on Linux with Docker."),
    ("Machine Learning Engineer", "MLOps, model serving, monitoring and reproducible machine learning pipelines."),
    ("AI Engineer", "NLP and computer vision with transformers, embeddings and deep learning APIs."),
    ("AI Engineer", "Build AI products using natural language processing, object detection and model serving."),
    ("Web Developer", "Responsive websites with HTML, CSS, JavaScript, Bootstrap and React."),
    ("Web Developer", "Frontend development, accessibility, SEO and web security for modern browsers."),
    ("Full Stack Developer", "Full stack web applications with React, Node.js, Express, MySQL and REST APIs."),
    ("Full Stack Developer", "Design database schemas, build authentication and deploy web applications with Docker."),
    ("Cybersecurity Analyst", "Monitor SIEM alerts in Splunk, analyse network traffic and respond to security incidents."),
    ("Cybersecurity Analyst", "Penetration testing, OWASP web security, cryptography and Linux hardening."),
]


def rank_text(query: str, careers: list[dict]) -> list[dict]:
    scores = career_matcher.text_scores(query, careers)
    rows = [
        {
            "career": career["name"],
            "id": int(career["id"]),
            "score": float(scores[int(career["id"])]["score"]),
            "cosine": float(scores[int(career["id"])]["cosine"]),
            "matched": scores[int(career["id"])]["matched"],
        }
        for career in careers
    ]
    rows.sort(key=lambda row: (-row["score"], -row["cosine"], row["career"]))
    return rows


def main() -> int:
    failures: list[str] = []
    checks = 0

    careers = load_careers()
    heading("A5 - Career recommendation")
    print(f"Careers : {len(careers)}")
    print(f"Queries : {len(QUERIES)} (hand-labelled, 2 per career)")

    section("Interest matcher: per-query result")
    top1_hits = 0
    top3_hits = 0
    reciprocal_rank_sum = 0.0

    for expected, query in QUERIES:
        ranked = rank_text(query, careers)
        names = [row["career"] for row in ranked]
        rank = names.index(expected) + 1 if expected in names else None
        top1_hits += int(rank == 1)
        top3_hits += int(rank is not None and rank <= 3)
        reciprocal_rank_sum += (1.0 / rank) if rank else 0.0
        marker = "OK " if rank == 1 else f"#{rank}"
        print(f"  [{marker}] expected {expected:<26} got {names[0]:<26} "
              f"score={ranked[0]['score']:.3f}")
        if rank != 1:
            print(f"        top-3: {', '.join(names[:3])}")

    total = len(QUERIES)
    top1_accuracy = top1_hits / total
    top3_accuracy = top3_hits / total
    mrr = reciprocal_rank_sum / total
    checks += 1
    if not (0.0 <= top1_accuracy <= 1.0 and 0.0 <= mrr <= 1.0):
        failures.append("interest metrics outside [0, 1]")

    print()
    print(f"Top-1 accuracy : {top1_hits}/{total} ({top1_accuracy * 100:.1f}%)")
    print(f"Top-3 accuracy : {top3_hits}/{total} ({top3_accuracy * 100:.1f}%)")
    print(f"MRR            : {mrr:.4f}")
    print("Note: a 16-statement synthetic benchmark, not real-world accuracy.")

    section("Score calibration gain")
    print("The gain multiplies every interest score, so ranking is invariant:")
    base_order = [row["career"] for row in rank_text(QUERIES[0][1], careers)]
    for gain in (1.0, 2.0, 3.0, 4.0):
        old_gain = Config.RECOMMEND_TEXT_GAIN
        try:
            Config.RECOMMEND_TEXT_GAIN = gain
            order = [row["career"] for row in rank_text(QUERIES[0][1], careers)]
        finally:
            Config.RECOMMEND_TEXT_GAIN = old_gain
        same = order == base_order
        checks += 1
        print(f"{'PASS' if same else 'FAIL'}  gain={gain:.1f} keeps the same ranking")
        if not same:
            failures.append(f"gain {gain} changed the ranking unexpectedly")

    section("Matcher edge cases")
    empty = career_matcher.text_scores("", careers)
    checks += 1
    passed = all(item["score"] == 0.0 and item["cosine"] == 0.0 for item in empty.values())
    print(f"{'PASS' if passed else 'FAIL'}  empty query returns zero scores")
    if not passed:
        failures.append("empty query returned non-zero scores")

    stopwords = career_matcher.text_scores("the and for with you your", careers)
    checks += 1
    passed = all(item["score"] == 0.0 for item in stopwords.values())
    print(f"{'PASS' if passed else 'FAIL'}  stopword-only query returns zero scores")
    if not passed:
        failures.append("stopword-only query returned non-zero scores")

    no_careers = career_matcher.text_scores("python", [])
    checks += 1
    print(f"{'PASS' if no_careers == {} else 'FAIL'}  no careers -> empty result")
    if no_careers != {}:
        failures.append("text_scores did not handle an empty career list")

    section("Hybrid ranker on a seeded student")
    student_id = 2
    student = student_model.get_by_id(student_id)
    if not student:
        failures.append(f"seeded student {student_id} not found")
        return summary(failures, checks)

    analyses = gap_service.analyze_all(student_id)
    student_text = career_matcher.build_student_text(student)
    first = career_matcher.rank_careers(analyses, student_text, careers)
    second = career_matcher.rank_careers(analyses, student_text, careers)
    checks += 1
    deterministic = [row["career"]["name"] for row in first] == [
        row["career"]["name"] for row in second
    ]
    print(f"{'PASS' if deterministic else 'FAIL'}  deterministic ranking across two calls")
    if not deterministic:
        failures.append("rank_careers is not deterministic")

    scores_in_range = all(0.0 <= row["final_score"] <= 100.0 for row in first)
    sorted_desc = all(
        first[i]["final_score"] >= first[i + 1]["final_score"]
        for i in range(len(first) - 1)
    )
    checks += 1
    print(f"{'PASS' if scores_in_range and sorted_desc else 'FAIL'}  scores in [0,100] and sorted descending")
    if not (scores_in_range and sorted_desc):
        failures.append("hybrid scores out of range or unsorted")

    max_error = 0.0
    blend_errors = 0
    for row in first:
        blend = row["blend"]
        recomputed = (
            float(blend["readiness"]) * float(row["readiness"])
            + float(blend["text"]) * float(row["text_similarity"])
        )
        max_error = max(max_error, abs(round(recomputed, 2) - float(row["final_score"])))
        if abs(sum(blend.values()) - 1.0) > 1e-9:
            blend_errors += 1
    checks += 1
    print(f"{'PASS' if max_error <= 0.011 else 'FAIL'}  final score equals blend x signals "
          f"(max error {max_error:.4f})")
    if max_error > 0.011:
        failures.append(f"hybrid score mismatch {max_error}")

    checks += 1
    print(f"{'PASS' if blend_errors == 0 else 'FAIL'}  blend weights sum to 1 on every row")
    if blend_errors:
        failures.append(f"{blend_errors} rows with blend weights not summing to 1")

    print()
    print(f"Student: {student['full_name']} | interests: {student_text[:80]}...")
    print(f"{'rank':>4}  {'career':<28} {'readiness':>9} {'interest':>8} {'final':>6}  fit")
    for index, row in enumerate(first, start=1):
        print(
            f"{index:>4}  {row['career']['name']:<28} "
            f"{row['readiness']:>8.2f}% {row['text_similarity']:>7.2f}% "
            f"{row['final_score']:>6.2f}  {row['fit']}"
        )

    section("Ablation: readiness-only vs text-only vs hybrid")
    readiness_only = sorted(first, key=lambda row: (-row["readiness"], row["career_id"]))
    text_only = sorted(first, key=lambda row: (-row["text_similarity"], row["career_id"]))
    hybrid = sorted(first, key=lambda row: (-row["final_score"], row["career_id"]))
    print(f"{'rank':>4}  {'readiness only':<28} {'text only':<28} {'hybrid':<28}")
    for index in range(min(5, len(first))):
        print(
            f"{index + 1:>4}  {readiness_only[index]['career']['name']:<28} "
            f"{text_only[index]['career']['name']:<28} "
            f"{hybrid[index]['career']['name']:<28}"
        )

    section("Blend renormalisation")
    for has_readiness, has_text in [(True, True), (True, False), (False, True), (False, False)]:
        gap_w, text_w = career_matcher.blend_weights(has_readiness, has_text)
        expected_total = (1.0 if has_readiness or has_text else 0.0)
        passed = abs(gap_w + text_w - expected_total) < 1e-9
        checks += 1
        print(
            f"{'PASS' if passed else 'FAIL'}  readiness={has_readiness!s:<5} "
            f"text={has_text!s:<5} -> ({gap_w:.2f}, {text_w:.2f})"
        )
        if not passed:
            failures.append(
                f"blend did not normalise for ({has_readiness}, {has_text})"
            )

    return summary(failures, checks)


if __name__ == "__main__":
    raise SystemExit(main())
