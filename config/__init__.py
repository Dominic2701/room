# This wrapper package shares the name "config" with source-code/framework/config,
# which holds the real settings, urls.py and asgi.py. Vercel imports this wrapper
# first, so without the line below Django cannot find "config.urls" and every page
# fails with ModuleNotFoundError. Adding the real folder to this package's search
# path makes config.urls (and anything else not defined here) resolve to it.
from pathlib import Path

__path__.append(
    str(Path(__file__).resolve().parents[1] / "source-code" / "framework" / "config")
    if (Path(__file__).resolve().parents[1] / "source-code").is_dir()
    else str(Path(__file__).resolve().parents[1] / "framework" / "config")
)
