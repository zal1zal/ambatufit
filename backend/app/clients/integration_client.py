from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.config import settings

VALID_STATUSES = frozenset({"available", "unavailable", "not_configured"})


class IntegrationClient:
    def _is_enabled(self) -> bool:
        base_url = (settings.INTEGRATION_API_BASE_URL or "").strip()
        if not base_url or "replace" in base_url:
            return False
        if settings.INTEGRATION_MODE == "mock" and not settings.PARTNER_CONTRACTS_CONFIRMED:
            return False
        return True

    def _service_headers(self, bearer_token: Optional[str] = None) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        token = (settings.INTEGRATION_API_TOKEN or "").strip()
        if token and not token.startswith("replace"):
            headers["X-Service-Token"] = token
        elif bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        return headers

    async def get_provider_status(self) -> Dict[str, str]:
        """
        Returns provider status for AmbatuNoutrish and AmbatuMove (ambatumove).
        Status: available | unavailable | not_configured
        """
        status = {
            "ambatunoutrish": "not_configured",
            "ambatumove": "not_configured",
        }
        base_url = (settings.INTEGRATION_API_BASE_URL or "").strip()
        if settings.INTEGRATION_MODE == "mock" or not base_url or "replace" in base_url:
            return status

        headers = {"X-Service-Token": settings.INTEGRATION_API_TOKEN}
        try:
            async with httpx.AsyncClient(timeout=settings.INTEGRATION_TIMEOUT_SECONDS) as client:
                res = await client.get(f"{base_url.rstrip('/')}/status", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    for provider in status:
                        value = data.get(provider)
                        status[provider] = value if value in VALID_STATUSES else "unavailable"
                else:
                    return {provider: "unavailable" for provider in status}
        except Exception:
            return {provider: "unavailable" for provider in status}

        return status

    async def get_foods(
        self, query: Optional[str] = None, bearer_token: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Fetches food & nutrition records from AmbatuNoutrish via off-STB integration service. Sends only sanitized query."""
        base_url = (settings.INTEGRATION_API_BASE_URL or "").strip()
        if not self._is_enabled():
            return [], "not_configured"
        try:
            async with httpx.AsyncClient(timeout=settings.INTEGRATION_TIMEOUT_SECONDS) as client:
                res = await client.get(
                    f"{base_url.rstrip('/')}/nutrition/foods",
                    params={"query": query} if query else {},
                    headers=self._service_headers(bearer_token),
                )
                if res.status_code != 200:
                    return [], "unavailable"
                data = res.json()
                p_status = data.get("provider_status", "unavailable")
                if p_status not in VALID_STATUSES:
                    p_status = "unavailable"
                return list(data.get("items") or []), p_status
        except Exception:
            return [], "unavailable"

    async def get_gyms(
        self, city: Optional[str] = None, bearer_token: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Fetches gym & fitness facility records from AmbatuMove via off-STB integration service. Sends only sanitized city."""
        base_url = (settings.INTEGRATION_API_BASE_URL or "").strip()
        if not self._is_enabled():
            return [], "not_configured"
        try:
            async with httpx.AsyncClient(timeout=settings.INTEGRATION_TIMEOUT_SECONDS) as client:
                res = await client.get(
                    f"{base_url.rstrip('/')}/fitness/gyms",
                    params={"city": city} if city else {},
                    headers=self._service_headers(bearer_token),
                )
                if res.status_code != 200:
                    return [], "unavailable"
                data = res.json()
                p_status = data.get("provider_status", "unavailable")
                if p_status not in VALID_STATUSES:
                    p_status = "unavailable"
                return list(data.get("items") or []), p_status
        except Exception:
            return [], "unavailable"


integration_client = IntegrationClient()
