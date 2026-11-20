import httpx
from typing import List, Dict, Any, Optional

MOCK_GYMS = [
    {
        "id": "gym-001",
        "name": "AmbatoMove Fitness Ganesha",
        "address": "Jl. Ganesha No. 10, Bandung",
        "latitude": -6.8915,
        "longitude": 107.6107,
        "facilities": ["Cardio Zone", "Free Weights", "Locker Room", "Shower"],
        "opening_hours": "06:00 - 22:00 WIB",
        "class_schedule": ["HIIT (Senin 18:30)", "Yoga (Rabu 07:00)", "BodyPump (Jumat 19:00)"],
        "provider_id": "ambatomove",
    },
    {
        "id": "gym-002",
        "name": "AmbatoMove Hub Dago",
        "address": "Jl. Ir. H. Juanda No. 84, Bandung",
        "latitude": -6.8850,
        "longitude": 107.6142,
        "facilities": ["Functional Training", "Weights", "Sauna", "Cafe"],
        "opening_hours": "24 Jam",
        "class_schedule": ["Spinning (Selasa 19:00)", "Pilates (Kamis 08:00)"],
        "provider_id": "ambatomove",
    },
]


class AmbatoMoveAdapter:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key

    async def get_gyms(self, city: Optional[str] = None) -> tuple[List[Dict[str, Any]], str]:
        """
        Fetches gym and fitness data and normalizes into AmbatuFit schema.
        Returns: (gyms_list, provider_status)
        """
        if not self.base_url:
            gyms = MOCK_GYMS
            if city:
                c = city.lower()
                gyms = [g for g in gyms if c in g["address"].lower() or c in g["name"].lower()]
            return gyms, "available"

        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{self.base_url}/gyms", params={"city": city}, headers=headers)
                if res.status_code == 200:
                    raw_data = res.json()
                    raw_items = raw_data.get("items", raw_data) if isinstance(raw_data, dict) else raw_data
                    normalized = []
                    for item in raw_items:
                        normalized.append({
                            "id": str(item.get("id", item.get("gym_id", "unknown"))),
                            "name": item.get("name", item.get("gym_name", "Gym Facility")),
                            "address": item.get("address", "Alamat tidak tersedia"),
                            "latitude": float(item.get("latitude", 0.0)),
                            "longitude": float(item.get("longitude", 0.0)),
                            "facilities": item.get("facilities", []),
                            "opening_hours": item.get("opening_hours", "08:00 - 20:00"),
                            "class_schedule": item.get("class_schedule", []),
                            "provider_id": "ambatomove",
                        })
                    return normalized, "available"
                else:
                    return [], "unavailable"
        except Exception:
            return [], "unavailable"

