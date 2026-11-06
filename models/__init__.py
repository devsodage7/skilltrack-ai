"""Data access layer for SkillTrack AI.

Every module here talks to MySQL only. Business rules belong in services/.
"""

from models.db import (  # noqa: F401
    close_pool,
    execute,
    execute_many,
    exists,
    health_check,
    init_pool,
    insert,
    query_all,
    query_one,
    scalar,
    transaction,
)

__all__ = [
    "close_pool",
    "execute",
    "execute_many",
    "exists",
    "health_check",
    "init_pool",
    "insert",
    "query_all",
    "query_one",
    "scalar",
    "transaction",
]
