import json
from app.contexts.personal_health_intelligence.screening import (
    evaluate_red_flags,
    extract_affirmative_codes,
)
from app.schemas.health import EvidenceEntry


def test_extract_affirmative_codes_handles_ddxplus_types_and_defaults():
    entries = [
        EvidenceEntry(evidence_code="E_91", value=True),
        EvidenceEntry(evidence_code="E_89", value=False),
        EvidenceEntry(evidence_code="E_56", value=5),
        EvidenceEntry(evidence_code="E_59", value=0),
        EvidenceEntry(evidence_code="E_55", value=["V_29"]),
        EvidenceEntry(evidence_code="E_57", value=["V_123"]),  # DDXPlus default "nowhere"
    ]
    assert extract_affirmative_codes(entries) == {"E_91", "E_56", "E_55"}


def test_unreviewed_default_rules_are_not_activated_as_clinical_triage():
    # Shipped rules/red_flags.reviewed.json is marked pending_clinical_review -> must stay inactive
    res = evaluate_red_flags(
        [
            EvidenceEntry(evidence_code="E_14", value=True),
            EvidenceEntry(evidence_code="E_66", value=True),
        ]
    )
    assert res.level == "none"
    assert res.rule_ids == []


def test_reviewed_rules_handle_match_partial_multi_match_and_none(tmp_path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(
        json.dumps(
            [
                {
                    "rule_id": "R-URGENT-1",
                    "evidence_codes": ["E_14", "E_66"],
                    "severity": "urgent",
                    "message": "Segera cari pertolongan medis.",
                    "source_url": "https://example.invalid/r1",
                    "reviewed_by": "Clinician A",
                    "reviewed_at": "2026-11-21T00:00:00Z",
                    "review_status": "reviewed",
                },
                {
                    "rule_id": "R-URGENT-2",
                    "evidence_codes": ["E_128"],
                    "severity": "urgent",
                    "message": "Segera cari pertolongan medis.",
                    "source_url": "https://example.invalid/r2",
                    "reviewed_by": "Clinician A",
                    "reviewed_at": "2026-11-21T00:00:00Z",
                    "review_status": "reviewed",
                },
                {
                    "rule_id": "R-UNREVIEWED",
                    "evidence_codes": ["E_91"],
                    "severity": "urgent",
                    "message": "Must never activate",
                    "source_url": "https://example.invalid/r3",
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "review_status": "pending_clinical_review",
                },
            ]
        ),
        encoding="utf-8",
    )

    # Partial input (only E_14 without E_66) does not trigger R-URGENT-1
    partial = evaluate_red_flags([EvidenceEntry(evidence_code="E_14", value=True)], rules_path=rules_file)
    assert partial.level == "none"

    # Unreviewed rule ignored even when evidence matches
    unrev = evaluate_red_flags([EvidenceEntry(evidence_code="E_91", value=True)], rules_path=rules_file)
    assert unrev.level == "none"
    assert "aman" not in unrev.message.lower()

    # Multiple urgent rules matching simultaneously returns all matched rule_ids
    multi = evaluate_red_flags(
        [
            EvidenceEntry(evidence_code="E_14", value=True),
            EvidenceEntry(evidence_code="E_66", value=True),
            EvidenceEntry(evidence_code="E_128", value=True),
        ],
        rules_path=rules_file,
    )
    assert multi.level == "urgent"
    assert set(multi.rule_ids) == {"R-URGENT-1", "R-URGENT-2"}
