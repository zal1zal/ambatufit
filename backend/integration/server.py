import os
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure .env is loaded for standalone Integration server execution
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

from integration.adapters.ambatunoutrish import AmbatuNoutrishAdapter
from integration.adapters.ambatomove import AmbatoMoveAdapter

app = FastAPI(
    title="AmbatuFit Off-STB Integration Service",
    description="Cross-group adapter service connecting AmbatuFit with AmbatuNoutrish and ambatomove APIs. Deployed outside STB.",
    version="1.0.0",
)

INTEGRATION_TOKEN = os.environ.get("INTEGRATION_API_TOKEN", "replace-for-external-host-integration-token")

noutrish_adapter = AmbatuNoutrishAdapter(
    base_url=os.environ.get("NUTRITION_PROVIDER_BASE_URL"),
    api_key=os.environ.get("NUTRITION_PROVIDER_API_KEY"),
)

ambatomove_adapter = AmbatoMoveAdapter(
    base_url=os.environ.get("GYM_PROVIDER_BASE_URL"),
    api_key=os.environ.get("GYM_PROVIDER_API_KEY"),
)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "ambatufit-integration",
    }


@app.get("/integration/v1/status")
async def get_status():
    _, n_status = await noutrish_adapter.get_foods()
    _, g_status = await ambatomove_adapter.get_gyms()
    return {
        "ambatunoutrish": n_status,
        "ambatomove": g_status,
    }


@app.get("/integration/v1/nutrition/foods")
async def get_nutrition_foods(
    query: Optional[str] = Query(None),
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    items, p_status = await noutrish_adapter.get_foods(query=query)
    return {
        "items": items,
        "total": len(items),
        "provider_status": p_status,
    }


@app.get("/integration/v1/fitness/gyms")
async def get_fitness_gyms(
    city: Optional[str] = Query(None),
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    items, p_status = await ambatomove_adapter.get_gyms(city=city)
    return {
        "items": items,
        "total": len(items),
        "provider_status": p_status,
    }
