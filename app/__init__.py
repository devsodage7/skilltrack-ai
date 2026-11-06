"""
SkillTrack AI - Flask application factory.

    from app import create_app
    app = create_app()

Design notes
------------
* Configuration comes from config.Config (which reads .env).
* The MySQL pool is created once per process.
* If the database is unreachable the app still boots and shows a setup
  page instead of a stack trace - much friendlier during a demo.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, render_template, request

from app.extensions import current_user
from app.utils.security import csrf_protect, csrf_token
from config import Config, ensure_directories, get_config
from models import db

__all__ = ["create_app"]


def create_app(config_object: Any = None) -> Flask:
    # FLASK_ENV decides whether development, testing or production settings
    # are applied. Pass an explicit class/dict to override (used by tests).
    config_object = config_object or get_config()

    app = Flask(
        __name__,
        template_folder=str(Config.TEMPLATE_FOLDER),
        static_folder=str(Config.STATIC_FOLDER),
    )
    if isinstance(config_object, dict):
        app.config.update(config_object)
    else:
        app.config.from_object(config_object)

    # Behind Render / Fly / nginx the original scheme and host arrive in
    # X-Forwarded-* headers. ProxyFix makes url_for() and secure cookies work.
    if str(app.config.get("FLASK_ENV", "")).lower() == "production":
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    ensure_directories()
    _configure_logging(app)
    _init_database(app)
    _register_blueprints(app)
    _register_hooks(app)
    _register_error_handlers(app)
    _register_template_helpers(app)

    app.logger.info("SkillTrack AI started (env=%s)", app.config.get("FLASK_ENV"))
    return app


# ---------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------
def _configure_logging(app: Flask) -> None:
    log_dir = Path(app.config["LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    )
    handler.setLevel(getattr(logging, str(app.config.get("LOG_LEVEL", "INFO"))))

    if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
        app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, str(app.config.get("LOG_LEVEL", "INFO"))))


def _init_database(app: Flask) -> None:
    """Create the pool and probe the connection once at startup."""
    try:
        db.init_pool(app.config)
        status = db.health_check()
    except Exception as exc:  # noqa: BLE001 - reported on the setup page
        errno = getattr(exc, "errno", None)
        if errno == 1045:
            hint = (
                "MySQL rejected the login (error 1045). Open .env and set "
                "DB_PASSWORD to your MySQL root password, then restart."
            )
        elif errno == 2003:
            hint = (
                "MySQL server is not reachable (error 2003). Start the service "
                "with:  net start MySQL80"
            )
        elif errno == 1049:
            hint = (
                "Database does not exist (error 1049). Run: "
                "python database/init_db.py --reset"
            )
        else:
            hint = str(exc)
        app.logger.error("Database initialisation failed: %s", hint)
        status = {"ok": False, "error": hint, "errno": errno}

    app.config["DB_READY"] = bool(status.get("ok"))
    app.config["DB_STATUS"] = status
    if status.get("ok"):
        app.logger.info(
            "Database ready: %s (%s tables)", status.get("database"), status.get("tables")
        )
    else:
        app.logger.warning(
            "Database NOT ready: %s. Run: python database/init_db.py",
            status.get("error"),
        )


def _register_blueprints(app: Flask) -> None:
    from app.api import api_bp
    from app.admin import admin_bp
    from app.assessment import assessment_bp
    from app.auth import auth_bp
    from app.careers import careers_bp
    from app.performance import performance_bp
    from app.resume import resume_bp
    from app.roadmap import roadmap_bp
    from app.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(careers_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(roadmap_bp)
    app.register_blueprint(assessment_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)


def _register_hooks(app: Flask) -> None:
    @app.before_request
    def _before_request():
        # 1. CSRF for every state-changing request
        csrf_protect()

        # 2. Friendly setup page while the database is unavailable
        if not app.config.get("DB_READY", True):
            if request.endpoint in {"static", "api.health"}:
                return None
            return (
                render_template(
                    "errors/setup_required.html",
                    status=app.config.get("DB_STATUS", {}),
                    db_name=app.config.get("DB_NAME", "skilltrack_ai"),
                ),
                503,
            )
        return None

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


def _register_error_handlers(app: Flask) -> None:
    def _wants_json() -> bool:
        return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"

    def _render(code: int, title: str, message: str):
        if _wants_json():
            return jsonify({"ok": False, "error": message, "code": code}), code
        return render_template(f"errors/{code}.html", title=title, message=message), code

    @app.errorhandler(400)
    def bad_request(error):
        description = getattr(error, "description", None) or "The request could not be understood."
        return _render(400, "Bad request", description)

    @app.errorhandler(403)
    def forbidden(_error):
        return _render(403, "Access denied", "Your account does not have permission to open this page.")

    @app.errorhandler(404)
    def not_found(_error):
        return _render(404, "Page not found", "The page you requested does not exist or was moved.")

    @app.errorhandler(413)
    def too_large(_error):
        limit = app.config.get("MAX_UPLOAD_MB", 5)
        return _render(413, "File too large", f"The uploaded file is larger than the {limit} MB limit.")

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Unhandled error: %s", error)
        return _render(500, "Something went wrong", "An unexpected error occurred. Please try again.")

    @app.errorhandler(Exception)
    def unhandled(error):
        # Keep HTTP errors flowing through their own handlers
        from werkzeug.exceptions import HTTPException

        if isinstance(error, HTTPException):
            return error
        app.logger.exception("Unhandled exception")
        return _render(500, "Something went wrong", "An unexpected error occurred. Please try again.")


def _register_template_helpers(app: Flask) -> None:
    @app.context_processor
    def inject_globals():
        user = None
        try:
            user = current_user()
        except Exception:  # noqa: BLE001 - never break rendering for this
            user = None

        return {
            "current_user": user,
            "is_admin": bool(user and user.get("role") == "admin"),
            "csrf_token": csrf_token,
            "app_name": "SkillTrack AI",
            "disclaimer": app.config.get("RECOMMENDATION_DISCLAIMER", ""),
            "db_ready": app.config.get("DB_READY", True),
        }

    @app.template_filter("level_badge")
    def level_badge(level):
        try:
            value = float(level or 0)
        except (TypeError, ValueError):
            value = 0.0
        if value >= 4.5:
            return "success"
        if value >= 3.5:
            return "primary"
        if value >= 2.5:
            return "info"
        if value > 0:
            return "warning"
        return "secondary"
