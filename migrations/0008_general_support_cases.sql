ALTER TABLE support_cases
    ALTER COLUMN origin_service DROP NOT NULL;

ALTER TABLE support_cases
    ALTER COLUMN resource_type DROP NOT NULL;

ALTER TABLE support_cases
    ALTER COLUMN resource_id DROP NOT NULL;
