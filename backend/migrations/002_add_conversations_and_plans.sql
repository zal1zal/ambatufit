-- Migration 002: Conversation Memory & Personalized Health Plans (Personal Health Intelligence Context)

CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    title VARCHAR(160) NOT NULL,
    active_topic VARCHAR(160),
    summary TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations(user_id);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id VARCHAR(64) PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    role VARCHAR(24) NOT NULL,
    content TEXT NOT NULL,
    intent VARCHAR(64),
    citations_json TEXT NOT NULL DEFAULT '[]',
    safety_alert BOOLEAN NOT NULL DEFAULT 0,
    generation_mode VARCHAR(64),
    created_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_conv_id ON conversation_messages(conversation_id);

CREATE TABLE IF NOT EXISTS personalized_plans (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    parent_plan_id VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    goal VARCHAR(64) NOT NULL,
    profile_snapshot_json TEXT NOT NULL DEFAULT '{}',
    safety_level VARCHAR(32) NOT NULL DEFAULT 'none',
    safety_notes_json TEXT NOT NULL DEFAULT '[]',
    habits_json TEXT NOT NULL DEFAULT '[]',
    nutrition_section_json TEXT NOT NULL DEFAULT '{}',
    activity_section_json TEXT NOT NULL DEFAULT '{}',
    monitoring_guidance_json TEXT NOT NULL DEFAULT '[]',
    rag_citations_json TEXT NOT NULL DEFAULT '[]',
    clarification_questions_json TEXT NOT NULL DEFAULT '[]',
    revision_reason TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_personalized_plans_user_id ON personalized_plans(user_id);

