-- Migration 003: Account display_name persistence, Server-Side JWT Revocation, and Personal Nutrition Consumption Logs
-- Owned by Identity & Access Context and Personal Health Intelligence Context

ALTER TABLE users ADD COLUMN display_name VARCHAR(128);
ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1;

ALTER TABLE health_profiles ADD COLUMN display_name VARCHAR(128);

CREATE TABLE IF NOT EXISTS revoked_tokens (
    jti VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    revoked_at DATETIME NOT NULL,
    expires_at DATETIME NULL
);
CREATE INDEX IF NOT EXISTS ix_revoked_tokens_user_id ON revoked_tokens(user_id);

ALTER TABLE monitoring_entries ADD COLUMN meal_logs_json TEXT NOT NULL DEFAULT '[]';
