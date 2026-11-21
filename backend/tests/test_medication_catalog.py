from datetime import datetime, timedelta, timezone
import json
from app.db import MedicationCatalogItem
from app.schemas.medication import MEDICATION_DISCLAIMER, MEDICATION_UNAVAILABLE_MESSAGE


def _add_catalog_item(db_session, **overrides):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    defaults = {
        "id": "med-synth-001",
        "display_name": "Obat Bebas Sintetis A",
        "active_ingredient": "Kandungan Aktif Uji A",
        "category": "obat_bebas",
        "general_indications_json": json.dumps(["keluhan ringan umum", "nyeri ringan"]),
        "warnings_json": json.dumps(["Baca aturan pakai pada kemasan dan konsultasikan bila berlanjut."]),
        "contraindications_json": json.dumps(["Hipersensitivitas terhadap kandungan aktif."]),
        "source_reference_id": "synth-ref-001",
        "source_title": "Referensi Farmasi Uji Sintetis",
        "source_url": "https://example.invalid/reviewed-reference-001",
        "verified_at": now - timedelta(days=1),
        "expires_at": now + timedelta(days=30),
        "review_status": "reviewed",
        "review_version": "1.0.0",
    }
    defaults.update(overrides)
    item = MedicationCatalogItem(**defaults)
    db_session.add(item)
    db_session.commit()
    return item


def test_b_m02_default_unreviewed_catalog_returns_unavailable(client, demo_user_token):
    res = client.get("/api/v1/medications", headers={"Authorization": f"Bearer {demo_user_token}"})
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "items": [],
        "total": 0,
        "information_status": "unavailable",
        "message": MEDICATION_UNAVAILABLE_MESSAGE,
    }


def test_b_m01_b_m06_approved_catalog_search_and_detail_provenance(client, db_session, demo_user_token):
    _add_catalog_item(db_session, id="med-synth-001", display_name="Analgesik Uji A", category="obat_bebas")
    _add_catalog_item(
        db_session,
        id="med-synth-002",
        display_name="Antihistamin Uji B",
        active_ingredient="Zat Uji B",
        category="obat_bebas_terbatas",
        general_indications_json=json.dumps(["alergi ringan"]),
    )
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    # Search by query
    res = client.get("/api/v1/medications?query=analgesik", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["information_status"] == "available"
    assert data["total"] == 1
    item = data["items"][0]
    assert item["id"] == "med-synth-001"
    assert item["category"] == "obat_bebas"
    assert item["disclaimer"] == MEDICATION_DISCLAIMER
    assert item["source"]["verified_at"].endswith("Z")
    # B-M06: no dosage, prescription, purchase link, or individual suitability field
    for forbidden in ("dosage", "dose", "prescription", "buy_url", "price", "suitability"):
        assert forbidden not in item

    # Filter by indication
    ind_res = client.get("/api/v1/medications?indication=alergi", headers=headers)
    assert ind_res.status_code == 200
    assert [m["id"] for m in ind_res.json()["items"]] == ["med-synth-002"]

    # Valid standalone search with 0 hits remains available + empty (not a clinical safety finding)
    empty_res = client.get("/api/v1/medications?query=tidakada", headers=headers)
    assert empty_res.status_code == 200
    assert empty_res.json()["information_status"] == "available"
    assert empty_res.json()["items"] == []
    assert empty_res.json()["total"] == 0

    # Detail endpoint
    detail = client.get("/api/v1/medications/med-synth-001", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["source"]["reference_id"] == "synth-ref-001"
    assert len(detail.json()["warnings"]) > 0
    assert len(detail.json()["contraindications"]) > 0


def test_b_m02_unreviewed_stale_revoked_and_prescription_entries_excluded(client, db_session, demo_user_token):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _add_catalog_item(db_session, id="med-pending", review_status="pending_review")
    _add_catalog_item(db_session, id="med-revoked", review_status="revoked")
    _add_catalog_item(db_session, id="med-expired", expires_at=now - timedelta(minutes=5))
    _add_catalog_item(db_session, id="med-bad-url", source_url="http://insecure.invalid/ref")
    _add_catalog_item(db_session, id="med-rx", category="obat_keras")
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    res = client.get("/api/v1/medications", headers=headers)
    assert res.status_code == 200
    assert res.json()["information_status"] == "unavailable"
    assert res.json()["items"] == []

    for med_id in ("med-pending", "med-revoked", "med-expired", "med-bad-url", "med-rx", "nonexistent"):
        detail = client.get(f"/api/v1/medications/{med_id}", headers=headers)
        assert detail.status_code == 404
        assert detail.json()["error"]["code"] == "NOT_FOUND"


def test_medication_endpoints_require_user_role(client, demo_pro_token):
    unauth = client.get("/api/v1/medications")
    assert unauth.status_code == 401
    assert unauth.json()["error"]["request_id"]

    pro_denied = client.get("/api/v1/medications", headers={"Authorization": f"Bearer {demo_pro_token}"})
    assert pro_denied.status_code == 403
    assert pro_denied.json()["error"]["code"] == "FORBIDDEN"

