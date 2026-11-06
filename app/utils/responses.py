"""
Uniform JSON responses for fetch() calls and any future API surface.

Every payload has the same shape:
    {"ok": true,  "data": ...}
    {"ok": false, "error": "...", "details": {...}}
"""

from __future__ import annotations

import datetime as _dt
import decimal
from typing import Any

from flask import jsonify


def jsonable(value: Any) -> Any:
    """Recursively convert MySQL types into JSON-serialisable values."""
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat(sep=" ") if isinstance(value, _dt.datetime) else value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def ok(data: Any = None, status: int = 200, **meta):
    payload: dict[str, Any] = {"ok": True, "data": jsonable(data)}
    if meta:
        payload["meta"] = jsonable(meta)
    return jsonify(payload), status


def fail(message: str, status: int = 400, details: Any = None):
    payload: dict[str, Any] = {"ok": False, "error": message}
    if details is not None:
        payload["details"] = jsonable(details)
    return jsonify(payload), status
