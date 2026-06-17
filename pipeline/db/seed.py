import json
import sqlite3
from pathlib import Path

from pipeline.db.store import upsert_provider
from pipeline.state import ProviderRecord


def seed_db(conn: sqlite3.Connection) -> None:
    path = Path("data/sample_providers.json")
    records: list[dict] = json.loads(path.read_text())
    for r in records:
        upsert_provider(conn, ProviderRecord(**r))
    conn.commit()
