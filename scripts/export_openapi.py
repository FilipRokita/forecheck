"""Prints the API's OpenAPI document. `npm run api:types` turns it into TypeScript types."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from forecheck.entrypoints.http.app import create_app

print(json.dumps(create_app().openapi(), indent=2, sort_keys=True, ensure_ascii=False))
