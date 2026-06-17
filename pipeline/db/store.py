import json
import logging
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from pipeline.state import ProviderRecord

log = logging.getLogger(__name__)

_DB_PATH = Path("data/pipeline.db")
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_db() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    schema = _SCHEMA_PATH.read_text()
    conn.executescript(schema)
    conn.commit()


def get_provider(conn: sqlite3.Connection, provider_id: str) -> ProviderRecord | None:
    row = conn.execute(
        "SELECT * FROM providers WHERE provider_id = ?", (provider_id,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def upsert_provider(conn: sqlite3.Connection, record: ProviderRecord) -> None:
    conn.execute(
        """
        INSERT INTO providers
            (provider_id, npi, provider_name, specialty, practice_name,
             address, phone, website, active, last_verified_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(provider_id) DO UPDATE SET
            provider_name = excluded.provider_name,
            specialty = excluded.specialty,
            practice_name = excluded.practice_name,
            address = excluded.address,
            phone = excluded.phone,
            website = excluded.website,
            active = excluded.active,
            last_verified_date = excluded.last_verified_date
        """,
        (
            record["provider_id"], record["npi"], record["provider_name"],
            record["specialty"], record["practice_name"], record["address"],
            record["phone"], record["website"],
            int(record["active"]) if record["active"] is not None else None,
            record["last_verified_date"],
        ),
    )


def get_stale_providers(
    conn: sqlite3.Connection, days_threshold: int = 90
) -> list[ProviderRecord]:
    cutoff = (date.today() - timedelta(days=days_threshold)).isoformat()
    rows = conn.execute(
        "SELECT * FROM providers WHERE last_verified_date < ? OR last_verified_date IS NULL",
        (cutoff,),
    ).fetchall()
    return [_row_to_record(r) for r in rows]


def _row_to_record(row: sqlite3.Row) -> ProviderRecord:
    return ProviderRecord(
        provider_id=row["provider_id"],
        npi=row["npi"] or "",
        provider_name=row["provider_name"] or "",
        specialty=row["specialty"] or "",
        practice_name=row["practice_name"] or "",
        address=row["address"] or "",
        phone=row["phone"] or "",
        website=row["website"] or "",
        active=bool(row["active"]),
        last_verified_date=row["last_verified_date"] or "",
    )
