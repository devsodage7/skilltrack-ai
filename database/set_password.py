"""
Set or reset a SkillTrack AI password on the configured database.

Works against local MySQL and cloud MySQL (set DB_* / DB_SSL_MODE first).

    .\.venv\Scripts\python.exe database\set_password.py user@example.com
    .\.venv\Scripts\python.exe database\set_password.py user@example.com --admin

The password is prompted for, never passed on the command line, so it does
not end up in shell history.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.security import hash_password, password_errors  # noqa: E402
from config import Config  # noqa: E402
from models import db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Set a SkillTrack AI password.")
    parser.add_argument("email", help="student email address")
    parser.add_argument("--admin", action="store_true", help="also grant the admin role")
    args = parser.parse_args()

    email = args.email.strip().lower()
    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Repeat password: ")
    if password != confirm:
        print("Passwords do not match.")
        return 1

    problems = password_errors(password)
    if problems:
        print("Password rejected:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    db.init_pool(Config)
    row = db.query_one(
        "SELECT id, email, role, is_active FROM students WHERE email = %s",
        (email,),
    )
    if not row:
        print(f"No account found for {email}")
        return 1

    db.execute(
        "UPDATE students SET password_hash = %s WHERE id = %s",
        (hash_password(password), row["id"]),
    )
    if args.admin and row["role"] != "admin":
        db.execute("UPDATE students SET role = 'admin' WHERE id = %s", (row["id"],))

    print(f"Password updated for {email} (role: {'admin' if args.admin else row['role']}).")
    print("Restart the app if it is running with a cached session.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
