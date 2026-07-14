MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN last_active_at TEXT",
    "ALTER TABLE users ADD COLUMN referred_by INTEGER",
    "ALTER TABLE users ADD COLUMN referral_credits_month TEXT",
    "ALTER TABLE users ADD COLUMN referral_credits_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN drip_opt_out INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN total_purchases INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN first_tryon_at TEXT",
    "ALTER TABLE users ADD COLUMN paywall_shown_at TEXT",
    "ALTER TABLE generations ADD COLUMN style_guide_path TEXT",
    "ALTER TABLE generations ADD COLUMN style_guide_at TEXT",
]

NEW_TABLES = """
CREATE TABLE IF NOT EXISTS analytics_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS drip_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    drip_id TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    sent_at TEXT,
    cancelled INTEGER NOT NULL DEFAULT 0,
    UNIQUE(telegram_id, drip_id)
);

CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referee_id INTEGER NOT NULL UNIQUE,
    converted_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS generation_locks (
    telegram_id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL
);
"""
