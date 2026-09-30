"""Vercel build step: apply database migrations to the hosted database.

Vercel runs this after installing dependencies (see [tool.vercel.scripts] in
pyproject.toml) and collects static files on its own. Migrations run only when a
hosted database is configured, so builds without database settings still pass.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def database_configured():
    if any(os.getenv(n) for n in ("DATABASE_URL", "POSTGRES_URL", "MYSQL_URL")):
        return True
    return os.getenv("DB_ENGINE", "").lower() == "mysql" and bool(os.getenv("DB_HOST"))


def main():
    if not database_configured():
        print("No hosted database configured; skipping migrations.")
        return
    print("Applying database migrations...")
    subprocess.run(
        [sys.executable, str(ROOT / "manage.py"), "migrate", "--noinput"],
        check=True,
    )


if __name__ == "__main__":
    main()
