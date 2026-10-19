"""Apply infra/clickhouse/migrations/*.sql in file-name order (03 SS7).

init.sql only runs when the ClickHouse volume is first created, so schema
changes after that go through idempotent migration files applied here:

    docker compose --profile dev up -d
    py scripts/apply_clickhouse_migrations.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.storage.clickhouse import get_client

MIGRATIONS = REPO / "infra" / "clickhouse" / "migrations"


def statements(sql: str) -> list[str]:
    lines = [line.split("--", 1)[0] for line in sql.splitlines()]
    return [part.strip() for part in "\n".join(lines).split(";") if part.strip()]


def main() -> None:
    client = get_client()
    try:
        for path in sorted(MIGRATIONS.glob("*.sql")):
            for statement in statements(path.read_text(encoding="utf-8")):
                client.command(statement)
            print(f"applied {path.name}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
