"""Apply DiddiSupport PostgreSQL migrations exactly once."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg

MIGRATION_TABLE = "support_schema_migrations"


def migration_directory(value: str | None = None) -> Path:
    configured = value or os.getenv("MIGRATIONS_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "migrations"


def migration_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("[0-9][0-9][0-9][0-9]_*.sql"))


def asyncpg_dsn(database_url: str) -> str:
    """Convert SQLAlchemy's asyncpg URL to a DSN accepted by asyncpg."""
    if "+asyncpg" not in database_url:
        return database_url
    parts = urlsplit(database_url.replace("+asyncpg", "", 1))
    return urlunsplit(parts)


async def apply_migrations(database_url: str, directory: Path) -> list[str]:
    files = migration_files(directory)
    if not files:
        raise RuntimeError(f"No migration files found in {directory}")

    connection = await asyncpg.connect(asyncpg_dsn(database_url))
    try:
        await connection.execute(
            f"""CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )"""
        )
        applied = {
            row["filename"]
            for row in await connection.fetch(f"SELECT filename FROM {MIGRATION_TABLE}")
        }
        executed: list[str] = []
        for migration in files:
            if migration.name in applied:
                continue
            async with connection.transaction():
                await connection.execute(migration.read_text(encoding="utf-8"))
                await connection.execute(
                    f"INSERT INTO {MIGRATION_TABLE} (filename) VALUES ($1)", migration.name
                )
            executed.append(migration.name)
        return executed
    finally:
        await connection.close()


async def main() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for migrations")
    max_attempts = int(os.getenv("MIGRATION_MAX_ATTEMPTS", "30"))
    retry_seconds = float(os.getenv("MIGRATION_RETRY_SECONDS", "2"))
    directory = migration_directory()

    for attempt in range(1, max_attempts + 1):
        try:
            executed = await apply_migrations(database_url, directory)
            if executed:
                print(f"Applied migrations: {', '.join(executed)}", flush=True)
            else:
                print("Database already up to date", flush=True)
            return
        except (OSError, asyncpg.PostgresConnectionError) as error:
            if attempt == max_attempts:
                raise
            print(
                f"Database unavailable (attempt {attempt}/{max_attempts}): {error}",
                flush=True,
            )
            await asyncio.sleep(retry_seconds)


if __name__ == "__main__":
    asyncio.run(main())
