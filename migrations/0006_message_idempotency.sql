CREATE TABLE IF NOT EXISTS support_message_operations (
    idempotency_key VARCHAR(160) PRIMARY KEY,
    fingerprint VARCHAR(64) NOT NULL,
    message_id UUID NOT NULL REFERENCES support_case_messages(id),
    created_at TIMESTAMPTZ NOT NULL
);
