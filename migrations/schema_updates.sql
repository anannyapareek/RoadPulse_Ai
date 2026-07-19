-- migrations/schema_updates.sql
-- Additive schema changes only. Safe to run against the existing schema.sql.
-- Run once: sqlite3 instance/roadpulse.db < migrations/schema_updates.sql

-- ── 1. Citizen trust score (extends existing `devices` table) ──────────────
ALTER TABLE devices ADD COLUMN trust_score REAL DEFAULT 0.5;
ALTER TABLE devices ADD COLUMN verified_reports INTEGER DEFAULT 0;
ALTER TABLE devices ADD COLUMN false_reports INTEGER DEFAULT 0;
ALTER TABLE devices ADD COLUMN last_updated TEXT;

-- ── 2. Status column on incidents (used by community_validation) ────────────
-- Only add if not already present; SQLite ALTER TABLE ADD COLUMN is idempotent-safe
-- for new columns but errors if the column already exists. Run carefully.
ALTER TABLE incidents ADD COLUMN status TEXT DEFAULT 'PENDING';
ALTER TABLE incidents ADD COLUMN location_desc TEXT;  -- free-text location from Instagram reports
ALTER TABLE incidents ADD COLUMN source TEXT DEFAULT 'app';  -- 'app' | 'instagram'

-- ── 3. Executive summaries ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS summaries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    period_type TEXT    NOT NULL,   -- 'daily' | 'weekly' | 'monthly'
    period_start TEXT   NOT NULL,
    period_end   TEXT   NOT NULL,
    summary_text TEXT   NOT NULL,
    generated_at TEXT   NOT NULL
);

-- ── 4. Emergency call log ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS emergency_calls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL,
    call_sid    TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

-- ── 5. Instagram-linked device identities ───────────────────────────────────
CREATE TABLE IF NOT EXISTS device_socials (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT    NOT NULL,
    user_id   TEXT,
    handle    TEXT    NOT NULL,
    platform  TEXT    NOT NULL,   -- 'instagram' etc.
    UNIQUE(handle, platform)
);

-- ── 6. Community validation ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS incident_validations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL,
    device_id   TEXT    NOT NULL,
    vote        TEXT    NOT NULL,   -- 'confirm' | 'reject'
    note        TEXT,
    created_at  TEXT    NOT NULL,
    UNIQUE(incident_id, device_id),
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

CREATE TABLE IF NOT EXISTS incident_photos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL,
    file_path   TEXT    NOT NULL,
    uploaded_at TEXT    NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

-- ── 7. Dashboard routing audit log ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dashboard_routing_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT    NOT NULL,
    destination TEXT    NOT NULL,   -- 'admin' | 'user'
    reasoning   TEXT,
    source      TEXT    NOT NULL,   -- 'flag' | 'ai_tiebreak'
    created_at  TEXT    NOT NULL
);

-- ── 8. Users table (for login routing) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id             TEXT    PRIMARY KEY,
    is_admin            INTEGER,          -- NULL = ambiguous -> triggers AI tie-break
    total_reports       INTEGER DEFAULT 0,
    trust_score         REAL    DEFAULT 0.5,
    admin_actions_count INTEGER DEFAULT 0
);

-- ── 9. Training view for the RandomForest confidence model ──────────────────
-- Adjust joins/columns once your `incidents` table has real labeled outcomes.
CREATE VIEW IF NOT EXISTS incident_training_view AS
SELECT
    1.0                                                      AS base_score,
    CASE
        WHEN i.gps_accuracy IS NULL OR i.gps_accuracy <= 0 THEN 0.5
        ELSE MAX(0.5, MIN(1.0, 100.0 / i.gps_accuracy))
    END                                                      AS gps_accuracy_factor,
    CASE WHEN i.is_duplicate = 1 THEN 0.7 ELSE 1.0 END      AS duplicate_factor,
    COALESCE(d.trust_score, 0.5)                             AS device_trust_score,
    CAST(strftime('%H', i.created_at) AS INTEGER)            AS hour_of_day,
    CASE WHEN i.status = 'CONFIRMED' THEN 1.0 ELSE 0.0 END   AS image_validation_passed,
    CASE i.incident_type
        WHEN 'pothole'       THEN 0
        WHEN 'accident'      THEN 1
        WHEN 'flooding'      THEN 2
        WHEN 'debris'        THEN 3
        WHEN 'signal_outage' THEN 4
        WHEN 'congestion'    THEN 5
        WHEN 'crack'         THEN 6
        ELSE 7
    END                                                      AS incident_type_code,
    CASE
        WHEN i.status = 'CONFIRMED' THEN 1.0
        WHEN i.status = 'REJECTED'  THEN 0.0
        ELSE NULL
    END                                                      AS confirmed_valid
FROM incidents i
LEFT JOIN devices d ON d.device_id = i.device_id
WHERE i.status IN ('CONFIRMED', 'REJECTED');
