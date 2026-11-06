"""
SkillTrack AI - central configuration.

Every secret comes from environment variables (loaded from .env).
Nothing sensitive is hardcoded here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = folder that contains this file
BASE_DIR = Path(__file__).resolve().parent

# Load .env once, before any os.getenv() call
load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean env var accepting true/false, 1/0, yes/no."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class Config:
    """Base configuration used by the Flask app factory."""

    # ------------------------------------------------------
    # Flask core
    # ------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-only-insecure-key-change-me"
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = _env_bool("FLASK_DEBUG", True)

    # Session cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 hours

    # ------------------------------------------------------
    # MySQL
    # ------------------------------------------------------
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = _env_int("DB_PORT", 3306)
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "skilltrack_ai")
    DB_POOL_SIZE = _env_int("DB_POOL_SIZE", 5)
    DB_CHARSET = "utf8mb4"
    # Cloud MySQL providers (TiDB Cloud, Aiven, PlanetScale, ...) require TLS.
    #   disabled        -> plain local MySQL (default)
    #   required        -> encrypted, certificate NOT verified
    #   verify_ca       -> encrypted + CA verified (set DB_SSL_CA)
    #   verify_identity -> encrypted + CA + hostname verified
    DB_SSL_MODE = os.getenv("DB_SSL_MODE", "disabled").strip().lower()
    DB_SSL_CA = os.getenv("DB_SSL_CA", "").strip()

    # ------------------------------------------------------
    # Paths
    # ------------------------------------------------------
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    UPLOAD_FOLDER = BASE_DIR / "uploads" / "resumes"
    TEMPLATE_FOLDER = BASE_DIR / "templates"
    STATIC_FOLDER = BASE_DIR / "static"
    ARTIFACT_DIR = BASE_DIR / "ml" / "artifacts"
    LOG_DIR = BASE_DIR / "logs"

    # ------------------------------------------------------
    # Upload policy
    # ------------------------------------------------------
    MAX_UPLOAD_MB = _env_int("MAX_UPLOAD_MB", 5)
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf"}
    ALLOWED_MIME_TYPES = {"application/pdf"}
    PDF_MAGIC_BYTES = b"%PDF-"

    # ------------------------------------------------------
    # Optional local LLM (Ollama)
    # ------------------------------------------------------
    OLLAMA_ENABLED = _env_bool("OLLAMA_ENABLED", True)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    OLLAMA_TIMEOUT = _env_int("OLLAMA_TIMEOUT", 25)

    # ------------------------------------------------------
    # NLP
    # ------------------------------------------------------
    SPACY_ENABLED = _env_bool("SPACY_ENABLED", True)
    SPACY_MODEL = os.getenv("SPACY_MODEL", "en_core_web_sm")
    FUZZY_MATCH_THRESHOLD = 88  # 0-100, rapidfuzz WRatio score

    # ------------------------------------------------------
    # AI / scoring parameters (single source of truth)
    # ------------------------------------------------------
    # Weights used when fusing the three evidence sources (A3).
    # They are renormalised automatically over the available sources.
    FUSION_WEIGHTS = {
        "self": 0.30,
        "resume": 0.30,
        "quiz": 0.40,
    }

    # Accuracy -> level mapping used for assessment evidence (A2).
    # List of (minimum accuracy percent, awarded level), checked top-down.
    QUIZ_LEVEL_BANDS = (
        (90.0, 5.0),
        (75.0, 4.0),
        (60.0, 3.0),
        (40.0, 2.0),
        (0.0, 1.0),
    )
    QUIZ_MIN_QUESTIONS = 3  # fewer answers than this -> evidence rejected

    # Career ranker blend (A5)
    RECOMMEND_WEIGHT_GAP = 0.60
    RECOMMEND_WEIGHT_TEXT = 0.40
    RECOMMEND_MIN_READINESS_TO_SHOW = 0.0
    # TF-IDF interest coverage is a strict 0-1 ratio; a CV-style profile only
    # names a few interest terms, so the raw value is small by construction.
    # This gain calibrates 3-4 specific matching terms to a strong match.
    # It is a documented, ablatable constant (research experiment E5).
    RECOMMEND_TEXT_GAIN = 3.0

    # Roadmap (A6)
    ROADMAP_DEFAULT_HOURS_PER_SKILL = 6.0
    ROADMAP_MAX_WEEKS = 24

    # Readiness label thresholds
    READINESS_BANDS = (
        (85.0, "Career ready"),
        (70.0, "Nearly ready"),
        (50.0, "Developing"),
        (25.0, "Foundation stage"),
        (0.0, "Starting out"),
    )

    # Skill strength labels based on current/required ratio
    STRENGTH_BANDS = (
        (0.75, "strong"),
        (0.40, "intermediate"),
        (0.0001, "weak"),
        (0.0, "missing"),
    )

    # Clustering guard rails (admin analytics only)
    CLUSTER_MIN_STUDENTS = 8
    CLUSTER_K_RANGE = (2, 6)

    # Proficiency classifier guard rail
    MIN_LABELLED_ROWS_FOR_TRAINING = 60

    # Disclaimer shown wherever recommendations appear.
    RECOMMENDATION_DISCLAIMER = (
        "These recommendations are estimates generated from the evidence you provided "
        "(self-assessment, resume text and quiz performance). They are a learning guide, "
        "not a prediction of employment or a guarantee of career success."
    )

    # ------------------------------------------------------
    # Security / misc
    # ------------------------------------------------------
    # Werkzeug hash method. scrypt is also supported: "scrypt:32768:8:1"
    PASSWORD_HASH_METHOD = os.getenv(
        "PASSWORD_HASH_METHOD", "pbkdf2:sha256:600000"
    )
    LOGIN_MAX_ATTEMPTS = 10  # per session before a short cool-down
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class TestingConfig(Config):
    """Used by pytest - no debug, in-memory-safe defaults."""

    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    DB_NAME = os.getenv("TEST_DB_NAME", "skilltrack_ai_test")


class ProductionConfig(Config):
    """Hardened defaults for a real deployment."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True
    LOG_LEVEL = "WARNING"


CONFIG_MAP = {
    "development": Config,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def db_ssl_options(cfg=None) -> dict:
    """Translate DB_SSL_MODE / DB_SSL_CA into mysql-connector arguments.

    Works with either the Config class or a Flask app.config dict, so the
    web app and database/init_db.py share exactly one implementation.
    """
    def _get(key: str, default=None):
        if cfg is None:
            return getattr(Config, key, default)
        if isinstance(cfg, dict):
            return cfg.get(key, getattr(Config, key, default))
        return getattr(cfg, key, getattr(Config, key, default))

    mode = str(_get("DB_SSL_MODE", "disabled") or "disabled").strip().lower()
    ca = str(_get("DB_SSL_CA", "") or "").strip()

    if mode in {"disabled", "off", "false", "none", "0"}:
        return {"ssl_disabled": True}
    if mode in {"required", "on", "true", "1"}:
        return {
            "ssl_disabled": False,
            "ssl_verify_cert": False,
            "ssl_verify_identity": False,
        }
    if mode in {"verify_ca", "verify-ca"}:
        if not ca:
            raise ValueError(
                "DB_SSL_MODE=verify_ca requires DB_SSL_CA to point to a CA PEM file."
            )
        return {
            "ssl_disabled": False,
            "ssl_ca": ca,
            "ssl_verify_cert": True,
            "ssl_verify_identity": False,
        }
    if mode in {"verify_identity", "verify-identity"}:
        if not ca:
            raise ValueError(
                "DB_SSL_MODE=verify_identity requires DB_SSL_CA to point to a CA PEM file."
            )
        return {
            "ssl_disabled": False,
            "ssl_ca": ca,
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
        }
    raise ValueError(
        f"Unknown DB_SSL_MODE={mode!r}. Use disabled, required, verify_ca or verify_identity."
    )


def get_config(name: str | None = None):
    """Return a config class by name (defaults to FLASK_ENV)."""
    key = (name or os.getenv("FLASK_ENV") or "development").strip().lower()
    return CONFIG_MAP.get(key, Config)


def ensure_directories() -> None:
    """Create runtime folders that must exist before the app starts."""
    for path in (
        Config.UPLOAD_FOLDER,
        Config.ARTIFACT_DIR,
        Config.LOG_DIR,
        Config.BASE_DIR / "uploads",
    ):
        Path(path).mkdir(parents=True, exist_ok=True)
