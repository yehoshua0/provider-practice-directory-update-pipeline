import sqlite3

from pipeline.db.store import get_stale_providers
from pipeline.state import ProviderRecord


def detect_stale(conn: sqlite3.Connection, days: int = 90) -> list[ProviderRecord]:
    return get_stale_providers(conn, days_threshold=days)
