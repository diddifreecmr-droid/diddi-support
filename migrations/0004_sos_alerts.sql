CREATE TABLE IF NOT EXISTS support_sos_alerts (
    id UUID PRIMARY KEY,
    reporter_user_id UUID NOT NULL,
    origin_service VARCHAR(64) NOT NULL,
    case_id UUID,
    source_alert_id VARCHAR(160) UNIQUE,
    location_latitude DOUBLE PRECISION,
    location_longitude DOUBLE PRECISION,
    notification_status VARCHAR(20) NOT NULL,
    handling_status VARCHAR(20) NOT NULL,
    source_notification_sent BOOLEAN NOT NULL DEFAULT FALSE,
    notification_attempts INTEGER NOT NULL DEFAULT 0,
    escalation_level INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT support_sos_notification_status_ck CHECK (
        notification_status IN ('recorded', 'pending', 'sent', 'failed')
    ),
    CONSTRAINT support_sos_handling_status_ck CHECK (
        handling_status IN ('unconfirmed', 'confirmed', 'in_progress', 'completed')
    )
);

CREATE INDEX IF NOT EXISTS support_sos_queue_idx
    ON support_sos_alerts (handling_status, escalation_level, created_at);
