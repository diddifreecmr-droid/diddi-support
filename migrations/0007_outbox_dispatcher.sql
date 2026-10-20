ALTER TABLE support_cases
    ADD COLUMN IF NOT EXISTS aggregate_version INTEGER NOT NULL DEFAULT 1;

ALTER TABLE support_outbox_events
    ADD COLUMN IF NOT EXISTS aggregate_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE support_outbox_events
    ADD COLUMN IF NOT EXISTS lease_owner VARCHAR(120);
ALTER TABLE support_outbox_events
    ADD COLUMN IF NOT EXISTS lease_until TIMESTAMPTZ;
ALTER TABLE support_outbox_events
    ADD COLUMN IF NOT EXISTS last_error VARCHAR(500);
ALTER TABLE support_outbox_events
    ADD COLUMN IF NOT EXISTS quarantined_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS support_outbox_dispatch_idx
    ON support_outbox_events (next_attempt_at, created_at)
    WHERE published_at IS NULL AND quarantined_at IS NULL;
