import httpx
from app.config import settings
from integration.schemas import Gym


class AmbatuMoveAdapter:
    """AmbatuMove gym & fitness adapter. Missing coordinates/hours stay null, never invented."""

    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url
        self.api_key = api_key

    async def get_gyms(self, city=None):
        if not self.base_url or settings.INTEGRATION_MODE != "live" or not settings.PARTNER_CONTRACTS_CONFIRMED:
            return [], "not_configured"
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=settings.INTEGRATION_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{self.base_url.rstrip('/')}/gyms",
                    params={"city": city} if city else {},
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                items = data["items"] if isinstance(data, dict) else data
                if not isinstance(items, list):
                    raise ValueError("Invalid provider list")
                normalized = [
                    Gym.model_validate(
                        {
                            "id": str(item["id"]),
                            "name": item["name"],
                            "address": item.get("address"),
                            "latitude": item.get("latitude"),
                            "longitude": item.get("longitude"),
                            "facilities": item.get("facilities", []),
                            "opening_hours": item.get("opening_hours"),
                            "class_schedule": item.get("class_schedule", []),
                        }
                    ).model_dump()
                    for item in items
                ]
                return normalized, "available"
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return [], "unavailable"
