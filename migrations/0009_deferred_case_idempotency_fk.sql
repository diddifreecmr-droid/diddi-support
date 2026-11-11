-- Case creation claims the idempotency key before inserting the case row.
-- Defer the foreign-key check until transaction commit so the operation claim
-- and the case can still be written atomically.
ALTER TABLE support_case_operations
    DROP CONSTRAINT IF EXISTS support_case_operations_case_id_fkey;

ALTER TABLE support_case_operations
    ADD CONSTRAINT support_case_operations_case_id_fkey
    FOREIGN KEY (case_id)
    REFERENCES support_cases(id)
    DEFERRABLE INITIALLY DEFERRED;
