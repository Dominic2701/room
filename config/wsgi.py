import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1] / "source-code"
for import_dir in (
    PROJECT_DIR / "backend",
    PROJECT_DIR / "framework",
):
    if str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
