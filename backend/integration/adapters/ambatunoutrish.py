import os
import httpx
from app.config import settings
from integration.schemas import Food


class AmbatuNoutrishAdapter:
    """Provisional mapping, enabled only after the partner confirms its contract."""

    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url
        self.api_key = api_key

    async def get_foods(self, query=None):
        if not self.base_url or settings.INTEGRATION_MODE != 'live' or not settings.PARTNER_CONTRACTS_CONFIRMED:
            return [], 'not_configured'
        headers = {'X-API-Key': self.api_key} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(f"{self.base_url.rstrip('/')}/foods", params={'q': query} if query else {}, headers=headers)
                response.raise_for_status()
                data = response.json()
                items = data['items'] if isinstance(data, dict) else data
                if not isinstance(items, list):
                    raise ValueError('Invalid provider list')
                normalized = [Food.model_validate({
                    'id': str(item['id']), 'name': item['name'],
                    'calories_kcal': item.get('calories_kcal', item.get('calories')),
                    'protein_g': item.get('protein_g', item.get('protein')),
                    'carbs_g': item.get('carbs_g', item.get('carbs')),
                    'fat_g': item.get('fat_g', item.get('fat')),
                }).model_dump() for item in items]
                return normalized, 'available'
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return [], 'unavailable'
