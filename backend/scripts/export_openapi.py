import json
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from integration.server import app as integration_app

out_path = os.path.join(backend_dir, "contracts", "openapi.json")
schema = app.openapi()

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2, ensure_ascii=False)

print(f"OpenAPI schema successfully exported to {out_path}")

integration_path = os.path.join(backend_dir, 'contracts', 'integration-openapi.json')
with open(integration_path, 'w', encoding='utf-8') as f:
    json.dump(integration_app.openapi(), f, indent=2, ensure_ascii=False)
print(f'Integration schema successfully exported to {integration_path}')

