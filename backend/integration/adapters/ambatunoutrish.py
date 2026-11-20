import httpx
from typing import List, Dict, Any, Optional

MOCK_FOODS = [
    {
        "id": "nutri-001",
        "name": "Dada Ayam Panggang (100g)",
        "calories_kcal": 165,
        "protein_g": 31.0,
        "carbs_g": 0.0,
        "fat_g": 3.6,
        "provider_id": "ambatunoutrish",
    },
    {
        "id": "nutri-002",
        "name": "Nasi Merah Organik (1 porsi)",
        "calories_kcal": 215,
        "protein_g": 5.0,
        "carbs_g": 45.0,
        "fat_g": 1.8,
        "provider_id": "ambatunoutrish",
    },
    {
        "id": "nutri-003",
        "name": "Tumis Bayam Bawang Putih (1 mangkuk)",
        "calories_kcal": 70,
        "protein_g": 2.5,
        "carbs_g": 7.0,
        "fat_g": 3.0,
        "provider_id": "ambatunoutrish",
    },
    {
        "id": "nutri-004",
        "name": "Telur Rebus (1 butir)",
        "calories_kcal": 78,
        "protein_g": 6.3,
        "carbs_g": 0.6,
        "fat_g": 5.3,
        "provider_id": "ambatunoutrish",
    },
]


class AmbatuNoutrishAdapter:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key

    async def get_foods(self, query: Optional[str] = None) -> tuple[List[Dict[str, Any]], str]:
        """
        Fetches nutrition data and normalizes into AmbatuFit schema.
        Returns: (foods_list, provider_status)
        """
        # If no live URL is configured, use structured mock data
        if not self.base_url:
            foods = MOCK_FOODS
            if query:
                q = query.lower()
                foods = [f for f in foods if q in f["name"].lower()]
            return foods, "available"

        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{self.base_url}/foods", params={"q": query}, headers=headers)
                if res.status_code == 200:
                    raw_data = res.json()
                    raw_items = raw_data.get("items", raw_data) if isinstance(raw_data, dict) else raw_data
                    normalized = []
                    for item in raw_items:
                        normalized.append({
                            "id": str(item.get("id", item.get("food_id", "unknown"))),
                            "name": item.get("name", item.get("food_name", "Makanan")),
                            "calories_kcal": int(item.get("calories", item.get("calories_kcal", 0))),
                            "protein_g": float(item.get("protein", item.get("protein_g", 0.0))),
                            "carbs_g": float(item.get("carbs", item.get("carbs_g", 0.0))),
                            "fat_g": float(item.get("fat", item.get("fat_g", 0.0))),
                            "provider_id": "ambatunoutrish",
                        })
                    return normalized, "available"
                else:
                    return [], "unavailable"
        except Exception:
            return [], "unavailable"

