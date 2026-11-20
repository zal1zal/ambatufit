import pytest
from datetime import datetime, timedelta
from app.db import ProfessionalSlot, Booking


def test_b12_booking_collision_returns_409(client, db_session, demo_user_token):
    # Setup single slot
    now = datetime.utcnow()
    slot = ProfessionalSlot(
        id="slot-coll-01",
        professional_id="test-pro-01",
        starts_at=now + timedelta(days=2),
        ends_at=now + timedelta(days=2, hours=1),
        is_available=True,
    )
    db_session.add(slot)
    db_session.commit()

    # First booking -> Success 201
    res1 = client.post(
        "/api/v1/bookings",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={
            "professional_id": "test-pro-01",
            "slot_id": "slot-coll-01",
        },
    )
    assert res1.status_code == 201

    # Second booking on the same slot -> Conflict 409
    res2 = client.post(
        "/api/v1/bookings",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={
            "professional_id": "test-pro-01",
            "slot_id": "slot-coll-01",
        },
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "CONFLICT"

