#!/usr/bin/env python3
"""
Human review queue dashboard.
Usage:
    python review/dashboard.py              # list pending reviews
    python review/dashboard.py resolve <id> # mark item resolved
"""
import json
import sys

from pipeline.db.store import get_db, init_db


def list_pending(conn):
    rows = conn.execute(
        "SELECT id, provider_id, queued_at, overall_confidence, reason, diffs "
        "FROM review_queue WHERE resolved = 0 ORDER BY queued_at DESC"
    ).fetchall()

    if not rows:
        print("No pending reviews.")
        return

    print(f"\n{'ID':<5} {'Provider':<12} {'Queued':<22} {'Confidence':<12} Reason")
    print("-" * 90)
    for row in rows:
        print(f"{row['id']:<5} {row['provider_id']:<12} {row['queued_at'][:19]:<22} "
              f"{row['overall_confidence']:<12.2f} {row['reason'][:50]}")
        diffs = json.loads(row["diffs"] or "[]")
        for d in diffs:
            print(f"      {d['field']}: {d['old_value']!r} → {d['new_value']!r} "
                  f"[{d['confidence_score']:.2f}] sources={d['supporting_sources']}")
    print()


def resolve(conn, review_id: int):
    conn.execute("UPDATE review_queue SET resolved = 1 WHERE id = ?", (review_id,))
    conn.commit()
    print(f"Review {review_id} marked as resolved.")


def main():
    conn = get_db()
    init_db(conn)

    if len(sys.argv) >= 3 and sys.argv[1] == "resolve":
        resolve(conn, int(sys.argv[2]))
    else:
        list_pending(conn)

    conn.close()


if __name__ == "__main__":
    main()
