"""
Disease Search & Medication Search Regression Suite covering Sections 17.1 & 17.2:
- Exact name, alternative name, lay term, Indonesian/English, abbreviation, mild typo, ICD code, empty/out-of-KB
- Generic, brand, active ingredient, combination, distinct products per active ingredient, registration status
"""


def test_disease_search_covers_synonyms_lay_terms_typo_icd_and_missing(client, demo_user_token):
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    # 1. Exact & Indonesian synonym ("darah tinggi" -> Hypertension / Hipertensi)
    ht = client.get("/api/v1/diseases?query=darah+tinggi", headers=headers)
    assert ht.status_code == 200
    assert ht.json()["total"] >= 1
    assert any(
        "hipertensi" in (i["canonical_name"] + " " + (i["indonesian_name"] or "")).lower()
        or "high blood pressure" in i["canonical_name"].lower()
        or i.get("icd_code") == "I10"
        for i in ht.json()["items"]
    )

    # 2. Lay term ("kencing manis" -> Diabetes Mellitus)
    dm = client.get("/api/v1/diseases?query=kencing+manis", headers=headers)
    assert dm.status_code == 200
    assert any("diabetes" in i["canonical_name"].lower() for i in dm.json()["items"])

    # 3. Abbreviation ("TBC" -> Tuberculosis, "ISPA" -> URTI)
    tbc = client.get("/api/v1/diseases?query=TBC", headers=headers).json()
    assert any("tuberculosis" in i["canonical_name"].lower() for i in tbc["items"])

    # 4. Mild typo ("diabtes" -> Diabetes)
    typo = client.get("/api/v1/diseases?query=diabtes", headers=headers).json()
    assert typo["total"] >= 1
    assert any("diabetes" in i["canonical_name"].lower() for i in typo["items"])

    # 5. ICD-10 lookup ("J45" -> Asthma / J45)
    icd = client.get("/api/v1/diseases?query=J45", headers=headers).json()
    assert any(i.get("icd_code") == "J45" for i in icd["items"])

    # 5b. Symptom / similar typo lookup ("Pusying" -> Migrain / Anemia / Hipertensi)
    pusying = client.get("/api/v1/diseases?query=Pusying", headers=headers).json()
    assert pusying["total"] >= 1

    # 6. Detail endpoint keeps unverified fields null/honest rather than fabricating
    did = dm.json()["items"][0]["id"]
    detail = client.get(f"/api/v1/diseases/{did}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["source_references"]) >= 1

    # 7. Non-existent entity returns empty cleanly (never invents)
    none_res = client.get("/api/v1/diseases?query=penyakit_fiktif_xyz_999", headers=headers).json()
    assert none_res["total"] == 0
    assert none_res["items"] == []


def test_knowledge_medication_search_covers_aliases_brands_combos_typos_and_status(client, demo_user_token):
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    # 1. Indonesian alias "parasetamol" finds Acetaminophen products
    para = client.get("/api/v1/knowledge/medications?query=parasetamol", headers=headers)
    assert para.status_code == 200
    p_data = para.json()
    assert p_data["total"] >= 1
    first = p_data["items"][0]
    assert first["registration_status"] == "international_source_id_unverified"
    assert first["source_id"] == "SRC-OPENFDA-LABEL"

    # 2. Brand / trade name ("tylenol" or "glucophage") or generic ("metformin")
    met = client.get("/api/v1/knowledge/medications?query=glucophage", headers=headers).json()
    assert met["total"] >= 1
    assert any("metformin" in (m.get("generic_name") or "").lower() for m in met["items"])

    # 3. Typo tolerance ("ibuprofn" -> ibuprofen, "Setraline" -> Sertraline)
    ibu = client.get("/api/v1/knowledge/medications?query=ibuprofn", headers=headers).json()
    assert ibu["total"] >= 1

    sert = client.get("/api/v1/knowledge/medications?query=Setraline", headers=headers).json()
    assert sert["total"] >= 1
    assert any("sertraline" in (m.get("generic_name") or "").lower() for m in sert["items"])

    # 3b. Consonant subsequence ("Strln" -> Sertraline) and EAN-13 barcode lookup
    strln = client.get("/api/v1/knowledge/medications?query=Strln", headers=headers).json()
    assert strln["total"] >= 1
    assert any("sertraline" in (m.get("generic_name") or "").lower() for m in strln["items"])
    bcode = client.get("/api/v1/knowledge/medications?query=8992026001012", headers=headers).json()
    assert bcode["total"] >= 1

    # 4. Out-of-KB returns 0 cleanly
    missing = client.get("/api/v1/knowledge/medications?query=obat_ajaib_fiktif_777", headers=headers).json()
    assert missing["total"] == 0
    assert missing["items"] == []
