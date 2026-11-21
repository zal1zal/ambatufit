import json
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app

out_path = os.path.join(backend_dir, "contracts", "openapi.json")
schema = app.openapi()

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2, ensure_ascii=False)

print(f"OpenAPI schema successfully exported to {out_path}")

