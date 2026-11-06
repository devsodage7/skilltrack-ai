"""
Skill alias dictionary for resume extraction (algorithm A1).

Every canonical skill name stored in the `skills` table gets a list of
surface forms that a real CV might use. Multi-word and punctuation-heavy
forms are included on purpose: "node.js" and "nodejs" must both hit,
while "java" must not fire on "javascript" (word-boundary matching).

Keep this file data-only - no logic lives here.
"""

from __future__ import annotations

ALIASES: dict[str, tuple[str, ...]] = {
    # ---------------------------------------------------------- programming
    "Python": ("python", "python3", "py"),
    "Java": ("java", "java8", "java 11", "java 17"),
    "C++": ("c++", "cpp", "c plus plus"),
    "JavaScript": ("javascript", "js", "es6", "ecmascript"),
    "TypeScript": ("typescript", "ts"),
    "SQL": ("sql", "structured query language"),
    "R": ("r programming", "r language", "rstudio", "tidyverse"),
    "Bash/Shell Scripting": (
        "bash", "shell script", "shell scripting", "zsh", "powershell", "shell",
    ),
    # ------------------------------------------------------------ frameworks
    "HTML/CSS": ("html", "html5", "css", "css3", "flexbox", "css grid"),
    "Bootstrap": ("bootstrap",),
    "React": ("react", "react.js", "reactjs"),
    "Node.js": ("node.js", "nodejs", "node js", "express.js", "express"),
    "Flask": ("flask",),
    "Django": ("django",),
    "REST API Design": (
        "rest api", "restful", "rest apis", "api design", "http api", "rest",
    ),
    # ----------------------------------------------------------------- tools
    "Git": ("git", "version control"),
    "GitHub": ("github", "github actions", "pull request"),
    "Docker": ("docker", "dockerfile", "docker compose", "containerization"),
    "Linux": ("linux", "ubuntu", "debian", "centos", "red hat", "unix"),
    "Unit Testing": (
        "unit test", "unit testing", "unittest", "pytest", "junit", "tdd",
        "test case", "test cases",
    ),
    "CI/CD": (
        "ci/cd", "cicd", "continuous integration", "continuous deployment",
        "jenkins", "github actions",
    ),
    "Pandas": ("pandas", "dataframe", "dataframes"),
    "NumPy": ("numpy", "ndarray"),
    "Excel": ("excel", "microsoft excel", "spreadsheets", "vlookup", "pivot table"),
    "Power BI": ("power bi", "powerbi", "dax"),
    "Tableau": ("tableau",),
    "SIEM Tools": ("siem", "splunk", "elk stack", "qradar", "log analysis"),
    # --------------------------------------------------------------- concepts
    "Statistics": (
        "statistics", "statistical", "hypothesis testing", "regression analysis",
        "probability", "descriptive statistics",
    ),
    "Data Cleaning": (
        "data cleaning", "data wrangling", "data preprocessing", "missing values",
        "data quality",
    ),
    "Data Visualization": (
        "data visualization", "data visualisation", "matplotlib", "seaborn",
        "plotly", "dashboards", "charts",
    ),
    "ETL": ("etl", "extract transform load", "data pipeline", "airflow", "data pipelines"),
    "Machine Learning": (
        "machine learning", "supervised learning", "unsupervised learning",
        "model training", "ml model",
    ),
    "Deep Learning": (
        "deep learning", "neural network", "neural networks", "cnn", "rnn",
        "lstm", "transformer", "transformers",
    ),
    "Scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
    "TensorFlow": ("tensorflow", "keras"),
    "PyTorch": ("pytorch", "torch"),
    "NLP": (
        "nlp", "natural language processing", "text mining", "tokenization",
        "spacy", "nltk",
    ),
    "Computer Vision": (
        "computer vision", "opencv", "image processing", "object detection",
        "image classification",
    ),
    "Model Evaluation": (
        "model evaluation", "cross validation", "cross-validation", "confusion matrix",
        "precision recall", "f1 score", "roc auc", "hyperparameter tuning",
    ),
    "Feature Engineering": (
        "feature engineering", "feature selection", "feature extraction",
    ),
    "MLOps": ("mlops", "model deployment", "mlflow", "model monitoring"),
    "MySQL": ("mysql", "mariadb"),
    "PostgreSQL": ("postgresql", "postgres"),
    "MongoDB": ("mongodb", "mongo", "nosql"),
    "Database Design": (
        "database design", "normalization", "normalisation", "er diagram",
        "schema design", "database schema", "indexing",
    ),
    "Networking": (
        "networking", "tcp/ip", "dns", "http protocol", "subnetting",
        "osi model", "wireshark",
    ),
    "Cryptography": ("cryptography", "encryption", "hashing", "aes", "rsa", "tls"),
    "Web Security": (
        "web security", "owasp", "xss", "sql injection", "csrf", "secure coding",
    ),
    "Penetration Testing": (
        "penetration testing", "pentest", "pen testing", "ethical hacking",
        "kali linux", "burp suite", "metasploit",
    ),
    "Incident Response": (
        "incident response", "soc analyst", "security operations", "triage",
        "digital forensics", "malware analysis",
    ),
}

# Words that raise confidence when they appear next to a skill mention.
PROFICIENCY_WORDS: tuple[str, ...] = (
    "expert", "advanced", "proficient", "strong", "experienced", "solid",
    "hands-on", "hands on", "production", "professional",
)

# Words that lower confidence (a beginner mention is still evidence, but weak).
# "learning" is deliberately absent: it appears inside "machine learning",
# so it would penalise a perfectly strong CV.
WEAKNESS_WORDS: tuple[str, ...] = (
    "beginner", "basic", "familiar", "exposure", "introductory", "novice",
)

SECTION_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("experience", (
        "work experience", "professional experience", "experience", "internship",
        "internships", "employment", "industry experience",
    )),
    ("projects", ("projects", "project", "academic projects", "personal projects")),
    ("education", ("education", "academic background", "qualifications")),
    ("skills", ("skills", "technical skills", "technologies", "tech stack",
                "tools and technologies", "core competencies")),
    ("certifications", ("certifications", "certificates", "courses", "training")),
)


def aliases_for(canonical_name: str) -> tuple[str, ...]:
    """Aliases for one skill; falls back to the canonical name itself."""
    key = (canonical_name or "").strip()
    if key in ALIASES:
        return ALIASES[key]
    lowered = key.lower()
    for name, values in ALIASES.items():
        if name.lower() == lowered:
            return values
    return (key.lower(),) if key else ()
