"""
SkillTrack AI - application entry point.

    python run.py

Open http://127.0.0.1:5000 in your browser.
"""

from __future__ import annotations

import sys

from app import create_app
from config import Config

app = create_app()


if __name__ == "__main__":
    print("=" * 68)
    print("  SkillTrack AI")
    print(f"  Database : {Config.DB_NAME} @ {Config.DB_HOST}:{Config.DB_PORT}")
    print(f"  Ollama   : {'enabled' if Config.OLLAMA_ENABLED else 'disabled'}"
          f" (model {Config.OLLAMA_MODEL})")
    print("  URL      : http://127.0.0.1:5000")
    print("=" * 68)
    try:
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=bool(Config.DEBUG),
            use_reloader=False if "--no-reload" in sys.argv else True,
        )
    except OSError as exc:
        print(f"\nCould not start the server: {exc}")
        print("Port 5000 may already be in use. Stop the other process or change the port in run.py.")
        raise SystemExit(1)
