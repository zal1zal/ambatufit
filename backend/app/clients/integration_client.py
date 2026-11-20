import httpx
from typing import Dict, Any, List, Optional
from app.config import settings


class IntegrationClient:
    def __init__(self):
        self.base_url = settings.INTEGRATION_API_BASE_URL
        self.token = settings.INTEGRATION_API_TOKEN
        self.timeout = settings.INTEGRATION_TIMEOUT_SECONDS
        self.mode = settings.INTEGRATION_MODE

    async def get_provider_status(self) -> Dict[str, str]:
        """
        Returns provider status for AmbatuNoutrish and ambatomove.
        Status: available | unavailable | not_configured
        """
        if self.mode == "mock":
            return {
                "ambatunoutrish": "available",
                "ambatomove": "available",
            }
        
        status = {
            "ambatunoutrish": "not_configured",
            "ambatomove": "not_configured",
        }

        if not self.base_url or "replace" in self.base_url:
            return status

        headers = {"X-Service-Token": self.token}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.base_url}/status", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    status["ambatunoutrish"] = data.get("ambatunoutrish", "unavailable")
                    status["ambatomove"] = data.get("ambatomove", "unavailable")
                else:
                    status["ambatunoutrish"] = "unavailable"
                    status["ambatomove"] = "unavailable"
        except Exception:
            status["ambatunoutrish"] = "unavailable"
            status["ambatomove"] = "unavailable"

        return status


integration_client = IntegrationClient()

