#!/usr/bin/env python
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent / "source-code"
BACKEND_DIR = PROJECT_DIR / "backend"
FRAMEWORK_DIR = PROJECT_DIR / "framework"

for import_dir in (BACKEND_DIR, FRAMEWORK_DIR):
    if str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def main():
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is not installed. Run pip install -r requirements.txt."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
