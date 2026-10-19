CREATE TABLE IF NOT EXISTS support_case_operations (
    idempotency_key VARCHAR(160) PRIMARY KEY,
    fingerprint VARCHAR(64) NOT NULL,
    case_id UUID NOT NULL REFERENCES support_cases(id),
    created_at TIMESTAMPTZ NOT NULL
);

