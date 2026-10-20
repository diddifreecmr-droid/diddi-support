CREATE TABLE IF NOT EXISTS support_actions (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL,
    operation_key VARCHAR(160) NOT NULL UNIQUE,
    action_type VARCHAR(80) NOT NULL,
    requested_by VARCHAR(160) NOT NULL,
    status VARCHAR(20) NOT NULL,
    provider_reference VARCHAR(160),
    result_code VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT support_actions_status_ck CHECK (
        status IN ('requested', 'pending', 'succeeded', 'failed', 'unknown')
    )
);

CREATE INDEX IF NOT EXISTS support_actions_case_idx
    ON support_actions (case_id, created_at);
