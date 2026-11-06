"""
SkillTrack AI - data access layer (models/db.py)

Rules enforced in this module:
  * Every query is parameterised (%s placeholders). No string formatting.
  * Connections come from a bounded pool and are always returned.
  * Writers commit explicitly; failures roll back.
  * No Flask, no business logic, no ORM magic.

IMPORTANT: when you pass parameters, a literal percent sign inside the SQL
must be doubled. Use "LIKE %%python%%" when a params tuple is supplied.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterable, Sequence

import mysql.connector
from mysql.connector import Error, pooling

from config import Config, db_ssl_options

logger = logging.getLogger(__name__)

_pool: pooling.MySQLConnectionPool | None = None


# ---------------------------------------------------------------------
# Pool lifecycle
# ---------------------------------------------------------------------
def _cfg(cfg: Any, key: str, default: Any = None) -> Any:
    """Read a config value from a dict-like (Flask app.config) or an object."""
    if isinstance(cfg, dict):
        return cfg.get(key, default)
    return getattr(cfg, key, default)


def init_pool(config: Any = None) -> None:
    """Create the global connection pool. Safe to call more than once."""
    global _pool
    cfg = config or Config

    if _pool is not None:
        # Already initialised in this process (tests, reloader, factory reuse).
        return

    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name="skilltrack_pool",
            pool_size=int(_cfg(cfg, "DB_POOL_SIZE", 5)),
            pool_reset_session=True,
            host=_cfg(cfg, "DB_HOST", "127.0.0.1"),
            port=int(_cfg(cfg, "DB_PORT", 3306)),
            user=_cfg(cfg, "DB_USER", "root"),
            password=_cfg(cfg, "DB_PASSWORD", ""),
            database=_cfg(cfg, "DB_NAME", "skilltrack_ai"),
            charset=_cfg(cfg, "DB_CHARSET", "utf8mb4"),
            use_pure=True,
            connection_timeout=10,
            autocommit=False,
            **db_ssl_options(cfg),
        )
    except Error as exc:
        logger.error("Could not create MySQL pool: %s", exc)
        raise

    logger.info(
        "MySQL pool ready: %s@%s:%s/%s",
        _cfg(cfg, "DB_USER", "root"),
        _cfg(cfg, "DB_HOST", "127.0.0.1"),
        _cfg(cfg, "DB_PORT", 3306),
        _cfg(cfg, "DB_NAME", "skilltrack_ai"),
    )


def close_pool() -> None:
    """Release the pool reference (the driver cleans up connections)."""
    global _pool
    _pool = None


def _require_pool() -> pooling.MySQLConnectionPool:
    if _pool is None:
        raise RuntimeError(
            "Database pool is not initialised. Call models.db.init_pool() "
            "from the application factory before using the database."
        )
    return _pool


# ---------------------------------------------------------------------
# Context managers
# ---------------------------------------------------------------------
@contextmanager
def connection():
    """Borrow a pooled connection and always give it back."""
    pool = _require_pool()
    conn = pool.get_connection()
    try:
        if not conn.is_connected():
            conn.reconnect(attempts=1, delay=0)
        yield conn
    finally:
        try:
            conn.close()
        except Error:  # already closed - nothing to do
            pass


@contextmanager
def cursor(dictionary: bool = True, commit: bool = False):
    """
    Yield a buffered cursor.

    dictionary=True returns rows as dicts (what the app needs);
    set commit=True for INSERT / UPDATE / DELETE.
    """
    with connection() as conn:
        cur = conn.cursor(dictionary=dictionary, buffered=True)
        try:
            yield cur
            if commit:
                conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Error:
                pass
            raise
        finally:
            try:
                cur.close()
            except Error:
                pass


# ---------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------
def query_all(sql: str, params: Sequence[Any] = ()) -> list[dict]:
    """Return every row as a dict. Empty result -> empty list."""
    with cursor(dictionary=True) as cur:
        cur.execute(sql, tuple(params))
        return list(cur.fetchall() or [])


def query_one(sql: str, params: Sequence[Any] = ()) -> dict | None:
    """Return the first row as a dict, or None."""
    with cursor(dictionary=True) as cur:
        cur.execute(sql, tuple(params))
        return cur.fetchone()


def scalar(sql: str, params: Sequence[Any] = (), default: Any = None) -> Any:
    """Return the first column of the first row, or `default`."""
    row = query_one(sql, params)
    if not row:
        return default
    return next(iter(row.values()))


def exists(sql: str, params: Sequence[Any] = ()) -> bool:
    """Convenience wrapper for SELECT 1 ... style checks."""
    return query_one(sql, params) is not None


# ---------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------
def insert(sql: str, params: Sequence[Any] = ()) -> int:
    """Execute an INSERT and return the new AUTO_INCREMENT id."""
    with cursor(commit=True) as cur:
        cur.execute(sql, tuple(params))
        return int(cur.lastrowid or 0)


def execute(sql: str, params: Sequence[Any] = ()) -> int:
    """Execute UPDATE / DELETE and return the affected row count."""
    with cursor(commit=True) as cur:
        cur.execute(sql, tuple(params))
        return int(cur.rowcount or 0)


def execute_many(sql: str, rows: Iterable[Sequence[Any]]) -> int:
    """Bulk INSERT / UPDATE inside one transaction. Returns row count."""
    with cursor(commit=True) as cur:
        cur.executemany(sql, [tuple(r) for r in rows])
        return int(cur.rowcount or 0)


@contextmanager
def transaction():
    """
    Multi-statement transaction:

        with transaction() as cur:
            cur.execute(sql1, params1)
            cur.execute(sql2, params2)
    """
    with connection() as conn:
        cur = conn.cursor(dictionary=True, buffered=True)
        try:
            yield cur
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Error:
                pass
            raise
        finally:
            try:
                cur.close()
            except Error:
                pass


# ---------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------
def health_check() -> dict:
    """Small payload for a /health endpoint and the admin dashboard."""
    try:
        db = scalar("SELECT DATABASE()", default=None)
        version = scalar("SELECT VERSION()", default="unknown")
        tables = scalar(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
            (db,),
            default=0,
        )
        students = scalar("SELECT COUNT(*) FROM students", default=0)
        return {
            "ok": True,
            "database": db,
            "version": version,
            "tables": int(tables or 0),
            "students": int(students or 0),
        }
    except Exception as exc:  # noqa: BLE001 - reported to the caller
        logger.warning("Database health check failed: %s", exc)
        return {"ok": False, "error": str(exc)}
