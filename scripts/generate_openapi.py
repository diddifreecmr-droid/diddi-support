import json
from pathlib import Path

from diddi_support.main import app

schema = app.openapi()
request_id_header = {
    "description": "Correlation identifier echoed from the request or generated as UUID v4.",
    "schema": {"type": "string"},
}
for path in schema["paths"].values():
    for operation in path.values():
        if not isinstance(operation, dict) or "responses" not in operation:
            continue
        for response in operation["responses"].values():
            response.setdefault("headers", {})["X-Request-ID"] = request_id_header

output = Path(__file__).parents[1] / "docs" / "api" / "openapi.json"
output.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {output}")
