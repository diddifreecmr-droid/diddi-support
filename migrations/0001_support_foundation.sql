-- DiddiSupport Sprint 1 foundation.
-- Apply through the project's migration runner once PostgreSQL wiring lands.

CREATE TABLE IF NOT EXISTS support_cases (
    id UUID PRIMARY KEY,
    origin_service VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id UUID NOT NULL,
    origin_report_id VARCHAR(160),
    reporter_user_id UUID NOT NULL,
    category VARCHAR(80) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    status VARCHAR(32) NOT NULL,
    assigned_agent_id UUID,
    resolution_code VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    CONSTRAINT support_cases_priority_ck CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    CONSTRAINT support_cases_status_ck CHECK (
        status IN ('open', 'in_progress', 'waiting_user', 'waiting_internal', 'resolved', 'closed')
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS support_cases_origin_report_uq
    ON support_cases (origin_service, origin_report_id)
    WHERE origin_report_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS support_audit_events (
    id UUID PRIMARY KEY,
    action VARCHAR(120) NOT NULL,
    target_type VARCHAR(80) NOT NULL,
    target_id VARCHAR(160) NOT NULL,
    outcome VARCHAR(32) NOT NULL,
    actor_id UUID,
    request_id VARCHAR(160),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS support_outbox_events (
    id UUID PRIMARY KEY,
    event_type VARCHAR(160) NOT NULL,
    aggregate_type VARCHAR(80) NOT NULL,
    aggregate_id VARCHAR(160) NOT NULL,
    payload JSONB NOT NULL,
    correlation_id VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS support_outbox_pending_idx
    ON support_outbox_events (next_attempt_at, created_at)
    WHERE published_at IS NULL;

