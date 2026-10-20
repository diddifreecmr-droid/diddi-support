-- Official Sprint 4: messages and DiddiFiles references.

CREATE TABLE IF NOT EXISTS support_case_messages (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES support_cases(id),
    author_type VARCHAR(20) NOT NULL,
    author_id VARCHAR(160) NOT NULL,
    body VARCHAR(10000) NOT NULL,
    visibility VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT support_case_messages_visibility_ck CHECK (
        visibility IN ('user_visible', 'internal_note', 'system_event')
    )
);

CREATE INDEX IF NOT EXISTS support_case_messages_case_idx
    ON support_case_messages (case_id, created_at);

CREATE TABLE IF NOT EXISTS support_case_attachments (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES support_cases(id),
    file_id UUID NOT NULL,
    owner_user_id UUID NOT NULL,
    purpose VARCHAR(80) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT support_case_attachments_size_ck CHECK (size_bytes > 0)
);

CREATE INDEX IF NOT EXISTS support_case_attachments_case_idx
    ON support_case_attachments (case_id, created_at);
