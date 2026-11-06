"""
SkillTrack AI - database bootstrap (database/init_db.py)

Commands
--------
    python database/init_db.py             # create tables if missing, seed data
    python database/init_db.py --reset     # DROP everything, recreate, reseed
    python database/init_db.py --check     # connectivity + row counts only
    python database/init_db.py --check --validate   # + weight and DAG checks

The script reads database/schema.sql and every database/seed_*.sql file,
splits them into single statements (quote and comment aware) and executes
them on one connection.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mysql.connector  # noqa: E402
from mysql.connector import Error  # noqa: E402

from config import Config, db_ssl_options  # noqa: E402

DB_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = DB_DIR / "schema.sql"

SEED_FILES = [
    "seed_skills.sql",
    "seed_careers.sql",
    "seed_career_skills.sql",
    "seed_students.sql",
    "seed_questions.sql",
    "seed_resources.sql",
    "seed_demo_activity.sql",
]

REQUIRED_TABLES = [
    "students",
    "careers",
    "skills",
    "career_skills",
    "student_skills",
    "assessments",
    "questions",
    "quiz_results",
    "learning_resources",
    "learning_progress",
    "resume_records",
]

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("init_db")


# ---------------------------------------------------------------------
# SQL script handling
# ---------------------------------------------------------------------
def split_sql_statements(sql: str) -> list[str]:
    """
    Split a .sql file into individual statements.

    Handles:
      * single quotes, double quotes and backticks (with backslash escapes)
      * -- line comments, # line comments, /* block comments */
      * semicolons only when they are outside quotes/comments
    """
    statements: list[str] = []
    buf: list[str] = []
    i, n = 0, len(sql)
    in_single = in_double = in_backtick = False

    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""

        if not (in_single or in_double or in_backtick):
            # -- comment
            if ch == "-" and nxt == "-":
                while i < n and sql[i] != "\n":
                    i += 1
                continue
            # # comment
            if ch == "#":
                while i < n and sql[i] != "\n":
                    i += 1
                continue
            # /* block comment */
            if ch == "/" and nxt == "*":
                i += 2
                while i + 1 < n and not (sql[i] == "*" and sql[i + 1] == "/"):
                    i += 1
                i += 2
                continue

        # backslash escape inside quoted text
        if ch == "\\" and (in_single or in_double) and i + 1 < n:
            buf.append(sql[i : i + 2])
            i += 2
            continue

        if ch == "'" and not (in_double or in_backtick):
            in_single = not in_single
        elif ch == '"' and not (in_single or in_backtick):
            in_double = not in_double
        elif ch == "`" and not (in_single or in_double):
            in_backtick = not in_backtick

        if ch == ";" and not (in_single or in_double or in_backtick):
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
        else:
            buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def run_script(cur, path: Path) -> int:
    """Execute every statement in a .sql file. Returns statement count."""
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")

    sql = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql)
    for number, stmt in enumerate(statements, start=1):
        try:
            cur.execute(stmt)
            # Drain any result sets so the connection stays usable
            if cur.with_rows:
                cur.fetchall()
        except Error as exc:
            preview = " ".join(stmt.split())[:160]
            raise RuntimeError(
                f"{path.name}: statement {number} failed\n"
                f"  SQL: {preview}\n"
                f"  MySQL: {exc}"
            ) from exc
    return len(statements)


# ---------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------
def connect(use_database: bool = True):
    """Open a direct (non-pooled) connection for setup work."""
    kwargs = dict(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        charset="utf8mb4",
        autocommit=True,
        use_pure=True,
        connection_timeout=10,
        **db_ssl_options(Config),
    )
    if use_database:
        kwargs["database"] = Config.DB_NAME
    return mysql.connector.connect(**kwargs)


def friendly_error(exc: Error) -> str:
    code = getattr(exc, "errno", None)
    if code == 1045:
        return (
            "MySQL rejected the login (error 1045).\n"
            "  -> Open .env and set DB_USER / DB_PASSWORD to your MySQL credentials.\n"
            "  -> Test it with:  mysql -u root -p -e \"SELECT VERSION();\""
        )
    if code == 2003:
        return (
            "Cannot reach the MySQL server (error 2003).\n"
            "  -> Start the service:  net start MySQL80\n"
            "  -> Check DB_HOST and DB_PORT in .env"
        )
    if code == 1049:
        return (
            "Database does not exist yet (error 1049).\n"
            "  -> Run:  python database/init_db.py"
        )
    return f"MySQL error {code}: {exc}"


def table_exists(cur, name: str) -> bool:
    cur.execute(
        "SELECT COUNT(*) AS c FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        (Config.DB_NAME, name),
    )
    return cur.fetchone()["c"] > 0


def count_rows(cur, table: str) -> int:
    cur.execute(f"SELECT COUNT(*) AS c FROM `{table}`")
    return int(cur.fetchone()["c"])


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------
def validate(cur) -> list[str]:
    """Return a list of human readable problems (empty list = healthy)."""
    problems: list[str] = []

    for table in REQUIRED_TABLES:
        if not table_exists(cur, table):
            problems.append(f"missing table: {table}")

    if problems:
        return problems

    # 1. weights must sum to ~1.00 per career
    cur.execute(
        """
        SELECT c.id, c.name, ROUND(SUM(cs.weight), 2) AS total, COUNT(*) AS skills
        FROM careers c
        JOIN career_skills cs ON cs.career_id = c.id
        GROUP BY c.id, c.name
        ORDER BY c.id
        """
    )
    careers = cur.fetchall()
    if len(careers) != 8:
        problems.append(f"expected 8 careers, found {len(careers)}")
    for row in careers:
        if abs(float(row["total"]) - 1.0) > 0.011:
            problems.append(
                f"career '{row['name']}' weights sum to {row['total']} (expected 1.00)"
            )

    # 2. prerequisite graph must be acyclic inside each career
    cur.execute(
        """
        SELECT career_id, skill_id, prerequisite_skill_id
        FROM career_skills
        WHERE prerequisite_skill_id IS NOT NULL
        """
    )
    edges = cur.fetchall()
    graph: dict[int, set[int]] = {}
    for row in edges:
        graph.setdefault(int(row["career_id"]), set()).add(
            (int(row["skill_id"]), int(row["prerequisite_skill_id"]))
        )

    def has_cycle(career_id: int) -> bool:
        pairs = graph.get(career_id, set())
        deps: dict[int, list[int]] = {}
        for skill, prereq in pairs:
            deps.setdefault(skill, []).append(prereq)
        state: dict[int, int] = {}

        def visit(node: int) -> bool:
            if state.get(node) == 1:
                return True
            if state.get(node) == 2:
                return False
            state[node] = 1
            for nxt in deps.get(node, []):
                if visit(nxt):
                    return True
            state[node] = 2
            return False

        return any(visit(node) for node in list(deps))

    for career_id in graph:
        if has_cycle(career_id):
            problems.append(f"prerequisite cycle detected in career_id={career_id}")

    # 3. every seed user must have a real password hash
    cur.execute("SELECT COUNT(*) AS c FROM students WHERE password_hash NOT LIKE 'pbkdf2:%' AND password_hash NOT LIKE 'scrypt:%'")
    if cur.fetchone()["c"] > 0:
        problems.append("some students have a non-hashed password value")

    # 4. questions sanity
    cur.execute("SELECT COUNT(*) AS c FROM questions WHERE explanation IS NULL OR CHAR_LENGTH(explanation) < 10")
    if cur.fetchone()["c"] > 0:
        problems.append("some questions have a missing or too-short explanation")

    return problems


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Create and seed the SkillTrack AI database.")
    parser.add_argument("--reset", action="store_true", help="drop and rebuild all tables")
    parser.add_argument("--check", action="store_true", help="only verify connection and data")
    parser.add_argument("--validate", action="store_true", help="run integrity checks")
    args = parser.parse_args()

    log.info("Connecting to MySQL at %s:%s as %s", Config.DB_HOST, Config.DB_PORT, Config.DB_USER)
    if not Config.DB_PASSWORD:
        log.warning(
            "DB_PASSWORD is empty in .env. If your MySQL root user has a password, "
            "the connection will fail with error 1045."
        )

    try:
        conn = connect(use_database=False)
    except Error as exc:
        log.error(friendly_error(exc))
        return 1

    try:
        cur = conn.cursor(dictionary=True)

        if args.check:
            try:
                cur.execute(f"USE `{Config.DB_NAME}`")
            except Error as exc:
                log.error(friendly_error(exc))
                return 1
            if not table_exists(cur, "students"):
                log.error(
                    "Tables are missing. Run:  python database/init_db.py"
                )
                return 1
            log.info("Database: %s", Config.DB_NAME)
            for table in REQUIRED_TABLES:
                log.info("  %-20s %6d rows", table, count_rows(cur, table))
            if args.validate:
                problems = validate(cur)
                if problems:
                    log.error("Validation problems:")
                    for problem in problems:
                        log.error("  - %s", problem)
                    return 2
                log.info("Validation: OK")
            return 0

        # Create (or rebuild) the database and select it
        if args.reset:
            log.info("Reset requested: dropping and recreating database %s", Config.DB_NAME)
            cur.execute(f"DROP DATABASE IF EXISTS `{Config.DB_NAME}`")

        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
        )
        cur.execute(f"USE `{Config.DB_NAME}`")

        # Schema is applied only when the application tables are absent
        if not table_exists(cur, "students"):
            statements = run_script(cur, SCHEMA_FILE)
            log.info("schema.sql applied (%d statements)", statements)
        else:
            log.info("Tables already exist - schema.sql skipped (use --reset to rebuild)")

        # seeds are idempotent (INSERT IGNORE)
        for filename in SEED_FILES:
            path = DB_DIR / filename
            if not path.exists():
                log.warning("seed file missing, skipped: %s", filename)
                continue
            statements = run_script(cur, path)
            log.info("%-28s %d statements", filename, statements)

        log.info("")
        log.info("Row counts")
        for table in REQUIRED_TABLES:
            log.info("  %-20s %6d", table, count_rows(cur, table))

        problems = validate(cur)
        if problems:
            log.error("")
            log.error("Integrity problems found:")
            for problem in problems:
                log.error("  - %s", problem)
            return 2

        log.info("")
        log.info("Setup complete. Demo logins:")
        log.info("  admin@skilltrack.local       / Admin@123")
        log.info("  aarav.patil@skilltrack.local / Student@123")
        return 0

    except RuntimeError as exc:
        log.error("%s", exc)
        return 1
    except Error as exc:
        log.error(friendly_error(exc))
        return 1
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
