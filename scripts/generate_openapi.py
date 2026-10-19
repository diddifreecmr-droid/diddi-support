import json
from pathlib import Path

from diddi_support.main import app

output = Path(__file__).parents[1] / "docs" / "api" / "openapi.json"
output.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"Wrote {output}")
