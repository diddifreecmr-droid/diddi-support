-- Message creation claims the idempotency key before inserting the message
-- row. Defer the foreign-key check until transaction commit so the claim,
-- message, audit event and outbox event remain atomic.
ALTER TABLE support_message_operations
    DROP CONSTRAINT IF EXISTS support_message_operations_message_id_fkey;

ALTER TABLE support_message_operations
    ADD CONSTRAINT support_message_operations_message_id_fkey
    FOREIGN KEY (message_id)
    REFERENCES support_case_messages(id)
    DEFERRABLE INITIALLY DEFERRED;
