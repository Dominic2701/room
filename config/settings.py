from pathlib import Path
from runpy import run_path

_SETTINGS_PATH = (
    Path(__file__).resolve().parents[1]
    / "source-code"
    / "framework"
    / "config"
    / "settings.py"
)

globals().update(
    {
        name: value
        for name, value in run_path(str(_SETTINGS_PATH)).items()
        if not name.startswith("__")
    }
)
