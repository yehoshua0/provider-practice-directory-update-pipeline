import json
from datetime import datetime, timezone
import sqlite3

from pipeline.state import PipelineState


def log_decision(conn: sqlite3.Connection, state: PipelineState) -> None:
    now = datetime.now(timezone.utc).isoformat()
    record = state["record"]
    action = state["recommended_action"]
    reason = state["reason"]

    if not state["diffs"]:
        conn.execute(
            "INSERT INTO audit_log (provider_id, run_at, field, old_value, new_value, "
            "confidence_score, supporting_sources, action, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record["provider_id"], now, "all_fields", None, None,
             state["overall_confidence"], "[]", action, reason),
        )
    else:
        for diff in state["diffs"]:
            conn.execute(
                "INSERT INTO audit_log (provider_id, run_at, field, old_value, new_value, "
                "confidence_score, supporting_sources, action, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record["provider_id"], now, diff["field"],
                    diff["old_value"], diff["new_value"],
                    diff["confidence_score"],
                    json.dumps(diff["supporting_sources"]),
                    action, reason,
                ),
            )


def add_to_review_queue(conn: sqlite3.Connection, state: PipelineState) -> None:
    now = datetime.now(timezone.utc).isoformat()
    record = state["record"]
    conn.execute(
        "INSERT INTO review_queue (provider_id, queued_at, overall_confidence, diffs, reason) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            record["provider_id"], now, state["overall_confidence"],
            json.dumps(state["diffs"]), state["reason"],
        ),
    )
