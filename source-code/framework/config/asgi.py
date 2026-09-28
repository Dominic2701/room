import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

PROJECT_DIR = Path(__file__).resolve().parents[2]
for import_dir in (PROJECT_DIR / "backend", Path(__file__).resolve().parent.parent):
    if str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_asgi_application()
