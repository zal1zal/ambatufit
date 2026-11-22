-- Immutable migration: Medication Information & Safety Guidance supporting tables
-- Owned by Personal Health Intelligence Context (AmbatuFit internal)

CREATE TABLE IF NOT EXISTS medication_catalog_items (
    id VARCHAR(64) PRIMARY KEY,
    display_name VARCHAR(128) NOT NULL,
    active_ingredient VARCHAR(128) NOT NULL,
    category VARCHAR(32) NOT NULL CHECK (category IN ('obat_bebas', 'obat_bebas_terbatas')),
    general_indications_json TEXT NOT NULL DEFAULT '[]',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    contraindications_json TEXT NOT NULL DEFAULT '[]',
    source_reference_id VARCHAR(128) NOT NULL,
    source_title VARCHAR(255) NOT NULL,
    source_url VARCHAR(512) NOT NULL,
    verified_at DATETIME NULL,
    expires_at DATETIME NULL,
    review_status VARCHAR(32) NOT NULL DEFAULT 'pending_review',
    review_version VARCHAR(32) NOT NULL DEFAULT '1.0.0'
);

CREATE TABLE IF NOT EXISTS medication_information_mappings (
    id VARCHAR(64) PRIMARY KEY,
    indication_key VARCHAR(64) NOT NULL,
    evidence_codes_json TEXT NOT NULL DEFAULT '[]',
    medication_id VARCHAR(64) NOT NULL REFERENCES medication_catalog_items(id),
    rule_id VARCHAR(64) NOT NULL,
    source_reference_id VARCHAR(128) NOT NULL,
    review_status VARCHAR(32) NOT NULL DEFAULT 'pending_review',
    review_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    expires_at DATETIME NULL
);

CREATE INDEX IF NOT EXISTS ix_medication_mappings_indication_key
    ON medication_information_mappings(indication_key);

CREATE INDEX IF NOT EXISTS ix_medication_mappings_medication_id
    ON medication_information_mappings(medication_id);

