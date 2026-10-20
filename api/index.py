"""Vercel entrypoint: a thin shim, so the package can live outside ``api/``.

Vercel turns every Python file in ``api/`` into a function. Keeping the code in
``backend/`` means only this file is one. The path insert makes ``forecheck``
importable; locally ``pyproject.toml`` does that for the tools.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from forecheck.entrypoints.http.app import create_app

app = create_app()
