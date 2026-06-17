CREATE TABLE IF NOT EXISTS providers (
    provider_id TEXT PRIMARY KEY,
    npi TEXT UNIQUE,
    provider_name TEXT,
    specialty TEXT,
    practice_name TEXT,
    address TEXT,
    phone TEXT,
    website TEXT,
    active INTEGER DEFAULT 1,
    last_verified_date TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id TEXT NOT NULL,
    run_at TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    confidence_score REAL,
    supporting_sources TEXT,
    action TEXT NOT NULL,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id TEXT NOT NULL,
    queued_at TEXT NOT NULL,
    overall_confidence REAL,
    diffs TEXT,
    reason TEXT,
    resolved INTEGER DEFAULT 0
);
