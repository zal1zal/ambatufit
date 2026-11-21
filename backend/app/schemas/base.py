from datetime import datetime, timezone
from pydantic import BaseModel, field_serializer


class ApiModel(BaseModel):
    """SQLite stores naive UTC; every public timestamp includes its UTC offset."""

    @field_serializer('*', check_fields=False)
    def serialize_utc(self, value):
        if isinstance(value, datetime):
            aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
            return aware.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        return value
