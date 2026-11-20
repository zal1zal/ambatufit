import pytest


def test_b15_partner_key_authorization_and_scopes(client):
    # Call with valid partner key
    res = client.get(
        "/api/v1/partner/professionals?specialty=doctor",
        headers={"X-API-Key": "noutrish-sec-key-123"},
    )
    assert res.status_code == 200
    assert "items" in res.json()

    # Call with invalid partner key -> MUST return 401
    bad_res = client.get(
        "/api/v1/partner/professionals",
        headers={"X-API-Key": "invalid-key-xyz"},
    )
    assert bad_res.status_code == 401
    assert bad_res.json()["error"]["code"] == "UNAUTHORIZED"

    # Partner cannot access private patient profile routes
    unauth_profile = client.get(
        "/api/v1/profile",
        headers={"X-API-Key": "noutrish-sec-key-123"},
    )
    assert unauth_profile.status_code == 401

