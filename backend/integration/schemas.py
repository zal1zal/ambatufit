from typing import Literal
from pydantic import BaseModel, Field

ProviderStatus = Literal['available', 'unavailable', 'not_configured']


class Food(BaseModel):
    id: str
    name: str
    calories_kcal: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    provider_id: Literal['ambatunoutrish'] = 'ambatunoutrish'


class Gym(BaseModel):
    id: str
    name: str
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    facilities: list[str] = Field(default_factory=list)
    opening_hours: str | None = None
    class_schedule: list[str] = Field(default_factory=list)
    provider_id: Literal['ambatumove'] = 'ambatumove'


class FoodList(BaseModel):
    items: list[Food]
    total: int
    provider_status: ProviderStatus


class GymList(BaseModel):
    items: list[Gym]
    total: int
    provider_status: ProviderStatus