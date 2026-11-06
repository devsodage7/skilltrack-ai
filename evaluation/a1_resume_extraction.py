"""
A1 - Resume skill extraction: precision, recall and false-positive guards.

Method
------
A small, hand-labelled benchmark of realistic CV text is run through the real
`ml.skill_extractor.extract_skills` against the real skills catalogue.
Each document has an expected set of canonical skill names. A detection is a
true positive only when the canonical name is in that set.

This is a synthetic benchmark written for the project. It is NOT a claim of
accuracy on real recruiters' CVs; it exists so the extraction logic can be
regression tested and its failure modes (abbreviation collisions, fuzzy
matching) are visible.

Run:
    .\\.venv\\Scripts\\python.exe evaluation/a1_resume_extraction.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.common import heading, load_skills, section, summary  # noqa: E402
from ml import skill_extractor  # noqa: E402

FIXTURES: list[dict] = [
    {
        "name": "python_backend",
        "text": """
Rahul Sharma
Python Backend Developer
Skills
Python, Flask, Django, SQL, MySQL, Git, Docker, Linux, REST API Design, Unit Testing
Projects
Built a Flask REST API for an inventory service with Python and MySQL.
Wrote unit tests with pytest and deployed the Docker image on Linux.
""",
        "expected": {
            "Python", "Flask", "Django", "SQL", "MySQL", "Git", "Docker",
            "Linux", "REST API Design", "Unit Testing",
        },
    },
    {
        "name": "data_analyst",
        "text": """
Priya Nair
Data Analyst
Skills
SQL, Excel, Power BI, Tableau, Python, Pandas, Statistics, Data Cleaning, Data Visualization
Experience
Cleaned sales data and built dashboards in Power BI and Tableau.
Used Excel pivot tables and SQL queries to report monthly KPIs.
Applied descriptive statistics and regression analysis to sales.
""",
        "expected": {
            "SQL", "Excel", "Power BI", "Tableau", "Python", "Pandas",
            "Statistics", "Data Cleaning", "Data Visualization",
        },
    },
    {
        "name": "data_scientist",
        "text": """
Dr. Ananya Rao
Data Scientist
Skills
Python, SQL, Pandas, NumPy, Scikit-learn, Machine Learning, Statistics, Feature Engineering, Model Evaluation, Data Visualization
Projects
Built a churn prediction model with scikit-learn and pandas.
Performed feature engineering and cross validation on customer data.
Compared models with a confusion matrix and ROC AUC.
Visualised results with matplotlib and seaborn.
""",
        "expected": {
            "Python", "SQL", "Pandas", "NumPy", "Scikit-learn",
            "Machine Learning", "Statistics", "Feature Engineering",
            "Model Evaluation", "Data Visualization",
        },
    },
    {
        "name": "ml_engineer",
        "text": """
Vikram Singh
Machine Learning Engineer
Skills
Python, Deep Learning, TensorFlow, PyTorch, Docker, Linux, Git, MLOps, Machine Learning
Experience
Trained neural networks with TensorFlow and PyTorch.
Built model deployment and model monitoring with MLflow on Linux.
Packaged training jobs in Docker and tracked versions in Git.
""",
        "expected": {
            "Python", "Deep Learning", "TensorFlow", "PyTorch", "Docker",
            "Linux", "Git", "MLOps", "Machine Learning",
        },
    },
    {
        "name": "ai_engineer",
        "text": """
Meera Iyer
AI Engineer
Skills
Python, NLP, Computer Vision, Deep Learning, PyTorch, TensorFlow, REST API Design
Projects
Built a natural language processing service for document classification.
Used tokenization and spaCy for text mining.
Trained a CNN for image classification and served it behind a REST API.
""",
        "expected": {
            "Python", "NLP", "Computer Vision", "Deep Learning", "PyTorch",
            "TensorFlow", "REST API Design",
        },
    },
    {
        "name": "web_developer",
        "text": """
Sneha Kulkarni
Web Developer
Skills
HTML, CSS, JavaScript, Bootstrap, React, Git, Web Security, REST API Design
Projects
Built responsive layouts with HTML5, CSS3 and Bootstrap.
Created reusable React components and fetched data from a REST API.
Fixed XSS issues following OWASP secure coding practices.
""",
        "expected": {
            "HTML/CSS", "JavaScript", "Bootstrap", "React", "Git",
            "Web Security", "REST API Design",
        },
    },
    {
        "name": "full_stack",
        "text": """
Arjun Deshmukh
Full Stack Developer
Skills
JavaScript, React, Node.js, Express, MySQL, SQL, Docker, Git, HTML, CSS, Database Design, REST API Design
Projects
Built a full stack web application with React and Node.js.
Designed a database schema in MySQL and wrote SQL queries.
Containerised the app with Docker and documented the REST API.
""",
        "expected": {
            "JavaScript", "React", "Node.js", "MySQL", "SQL", "Docker",
            "Git", "HTML/CSS", "Database Design", "REST API Design",
        },
    },
    {
        "name": "cybersecurity",
        "text": """
Karan Malhotra
Cybersecurity Analyst
Skills
Linux, Networking, Web Security, Cryptography, SIEM Tools, Penetration Testing, Incident Response
Experience
Monitored SIEM alerts in Splunk and analysed traffic with Wireshark.
Hardened Linux servers and reviewed OWASP risks such as XSS.
Supported incident response and digital forensics during malware analysis.
Performed penetration testing with Burp Suite and Metasploit.
Studied encryption, hashing and TLS for secure communication.
""",
        "expected": {
            "Linux", "Networking", "Web Security", "Cryptography",
            "SIEM Tools", "Penetration Testing", "Incident Response",
        },
    },
    {
        "name": "typo_fuzzy",
        "text": """
Nikhil Joshi
ML Enthusiast
Skills
Python, pytoch, tensorflow
Projects
Trained a small neural network in pytoch.
""",
        "expected": {"Python", "PyTorch", "TensorFlow", "Deep Learning"},
        "fuzzy_only": True,
    },
]

# Guard cases: the detector must return exactly these skill names.
GUARDS: list[tuple[str, str, set[str]]] = [
    ("javascript does not trigger java", "Senior JavaScript developer. Built React applications.", {"JavaScript", "React"}),
    ("excel inside excellent does not fire", "I am an excellent communicator.", set()),
    ("rest inside restaurant does not fire", "Managed a restaurant team for two years.", set()),
    ("classification alone is not computer vision", "Studied classification and regression notes.", set()),
    ("java and c++ are independent", "Wrote Java and C++ services.", {"Java", "C++"}),
    ("statistics aliases merge", "Learning statistics and probability.", {"Statistics"}),
    ("two skills in one sentence", "Built a machine learning model for image classification.", {"Machine Learning", "Computer Vision"}),
]

LEVEL_CASES: list[tuple[str, str, str, float, float]] = [
    (
        "skills list only is weak evidence",
        "Python",
        "Skills\nPython",
        0.0,
        1.0,
    ),
    (
        "projects plus proficiency is stronger",
        "Python",
        "Projects\nExpert Python developer. Built Python APIs. Python automation.",
        2.5,
        5.0,
    ),
]


def detected_names(result: dict) -> set[str]:
    return {str(row["name"]) for row in result["detected"]}


def level_of(result: dict, name: str) -> float:
    for row in result["detected"]:
        if row["name"] == name:
            return float(row["level"])
    return 0.0


def main() -> int:
    skills = load_skills()
    failures: list[str] = []
    checks = 0

    heading("A1 - Resume skill extraction on a labelled synthetic benchmark")
    print(f"Skills in catalogue : {len(skills)}")
    print(f"Labelled CVs        : {len(FIXTURES)}")

    section("Per-document results")
    print(f"{'document':<18} {'TP':>3} {'FP':>3} {'FN':>3}  {'precision':>9} {'recall':>7} {'F1':>6}")
    total_tp = total_fp = total_fn = 0
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []

    no_fuzzy_results: dict[str, set[str]] = {}
    for fixture in FIXTURES:
        text = fixture["text"]
        expected = set(fixture["expected"])
        result = skill_extractor.extract_skills(text, skills)
        found = detected_names(result)

        if fixture.get("fuzzy_only"):
            original_fuzz, original_process = skill_extractor.fuzz, skill_extractor.fuzz_process
            try:
                skill_extractor.fuzz = None
                skill_extractor.fuzz_process = None
                no_fuzzy_results[fixture["name"]] = detected_names(
                    skill_extractor.extract_skills(text, skills)
                )
            finally:
                skill_extractor.fuzz = original_fuzz
                skill_extractor.fuzz_process = original_process

        tp = len(found & expected)
        fp = len(found - expected)
        fn = len(expected - found)
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

        total_tp += tp
        total_fp += fp
        total_fn += fn
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

        print(
            f"{fixture['name']:<18} {tp:>3} {fp:>3} {fn:>3}  "
            f"{precision * 100:>8.1f}% {recall * 100:>6.1f}% {f1:>5.2f}"
        )
        if fp:
            print(f"    false positives: {', '.join(sorted(found - expected))}")
        if fn:
            print(f"    missed         : {', '.join(sorted(expected - found))}")

        checks += 1
        if not found:
            failures.append(f"{fixture['name']}: no skills detected at all")

    micro_precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if micro_precision + micro_recall
        else 0.0
    )

    section("Aggregate metrics")
    print(f"Micro precision : {micro_precision * 100:.2f}%  ({total_tp} TP / {total_tp + total_fp} detections)")
    print(f"Micro recall    : {micro_recall * 100:.2f}%  ({total_tp} TP / {total_tp + total_fn} expected)")
    print(f"Micro F1        : {micro_f1:.4f}")
    print(f"Macro precision : {sum(precisions) / len(precisions) * 100:.2f}%")
    print(f"Macro recall    : {sum(recalls) / len(recalls) * 100:.2f}%")
    print(f"Macro F1        : {sum(f1s) / len(f1s):.4f}")

    section("False-positive and boundary guards")
    for label, text, expected in GUARDS:
        found = detected_names(skill_extractor.extract_skills(text, skills))
        passed = found == expected
        checks += 1
        print(f"{'PASS' if passed else 'FAIL'}  {label:<42} found={sorted(found)}")
        if not passed:
            failures.append(f"guard '{label}': expected {sorted(expected)}, got {sorted(found)}")

    section("Evidence-level discrimination")
    for label, skill, text, minimum, maximum in LEVEL_CASES:
        result = skill_extractor.extract_skills(text, skills)
        level = level_of(result, skill)
        passed = minimum <= level <= maximum
        checks += 1
        print(f"{'PASS' if passed else 'FAIL'}  {label:<42} {skill} level={level:.1f}")
        if not passed:
            failures.append(f"level case '{label}': {level} outside [{minimum}, {maximum}]")

    section("Fuzzy matching ablation (typo document)")
    with_fuzzy = next(
        detected_names(skill_extractor.extract_skills(f["text"], skills))
        for f in FIXTURES if f.get("fuzzy_only")
    )
    without_fuzzy = no_fuzzy_results.get("typo_fuzzy", set())
    gained = with_fuzzy - without_fuzzy
    print(f"with fuzzy    : {sorted(with_fuzzy)}")
    print(f"without fuzzy : {sorted(without_fuzzy)}")
    print(f"fuzzy gains   : {sorted(gained)}")
    checks += 1
    if "PyTorch" not in gained:
        failures.append("fuzzy matching did not recover the 'pytoch' typo as PyTorch")

    return summary(failures, checks)


if __name__ == "__main__":
    raise SystemExit(main())
