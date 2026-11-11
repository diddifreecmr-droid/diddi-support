from pathlib import Path

from diddi_support.ops.migrate import asyncpg_dsn, migration_files


def test_migrations_are_discovered_in_order() -> None:
    files = migration_files(Path("migrations"))

    assert [path.name for path in files] == [
        "0001_support_foundation.sql",
        "0002_idempotency_operations.sql",
        "0003_messages_attachments.sql",
        "0004_sos_alerts.sql",
        "0005_support_actions.sql",
        "0006_message_idempotency.sql",
        "0007_outbox_dispatcher.sql",
        "0008_general_support_cases.sql",
        "0009_deferred_case_idempotency_fk.sql",
    ]


def test_asyncpg_dsn_removes_sqlalchemy_driver_suffix() -> None:
    assert asyncpg_dsn("postgresql+asyncpg://user:pass@db:5432/support") == (
        "postgresql://user:pass@db:5432/support"
    )


def test_case_idempotency_foreign_key_is_deferred() -> None:
    sql = Path("migrations/0009_deferred_case_idempotency_fk.sql").read_text(encoding="utf-8")

    assert "support_case_operations_case_id_fkey" in sql
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
