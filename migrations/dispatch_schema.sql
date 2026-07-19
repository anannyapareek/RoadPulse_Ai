-- migrations/dispatch_schema.sql
-- Dispatch Management & Incident Lifecycle Schema Updates
-- Run once: sqlite3 instance/roadpulse.db < migrations/dispatch_schema.sql

-- ── 1. Extend incidents table with dispatch and lifecycle fields ──────────────
ALTER TABLE incidents ADD COLUMN dispatch_status VARCHAR DEFAULT 'open';
ALTER TABLE incidents ADD COLUMN assigned_department VARCHAR;
ALTER TABLE incidents ADD COLUMN assigned_officer_id INTEGER;
ALTER TABLE incidents ADD COLUMN priority_level VARCHAR DEFAULT 'medium';
ALTER TABLE incidents ADD COLUMN eta_minutes INTEGER;
ALTER TABLE incidents ADD COLUMN dispatch_time DATETIME;
ALTER TABLE incidents ADD COLUMN resolved_time DATETIME;
ALTER TABLE incidents ADD COLUMN resolution_notes TEXT;

-- ── 2. Officers table: stores police/emergency responder information ──────────
CREATE TABLE IF NOT EXISTS officers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    badge_number VARCHAR UNIQUE NOT NULL,
    department VARCHAR NOT NULL,
    phone_number VARCHAR,
    email VARCHAR,
    rank VARCHAR,
    status VARCHAR DEFAULT 'active',
    location_lat FLOAT,
    location_lon FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── 3. Dispatch logs table: audit trail for all dispatch actions ─────────────
CREATE TABLE IF NOT EXISTS dispatch_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL,
    officer_id INTEGER,
    action_type VARCHAR NOT NULL,
    status_before VARCHAR,
    status_after VARCHAR,
    priority_before VARCHAR,
    priority_after VARCHAR,
    performed_by VARCHAR,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    FOREIGN KEY (incident_id) REFERENCES incidents (id) ON DELETE CASCADE,
    FOREIGN KEY (officer_id) REFERENCES officers (id) ON DELETE SET NULL
);

-- ── 4. Officer assignments table: tracks which officers are assigned to incidents ──
CREATE TABLE IF NOT EXISTS officer_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    officer_id INTEGER NOT NULL,
    incident_id INTEGER NOT NULL,
    assignment_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    dispatch_method VARCHAR,
    dispatch_status VARCHAR DEFAULT 'pending',
    acknowledgment_time DATETIME,
    estimated_arrival DATETIME,
    actual_arrival DATETIME,
    FOREIGN KEY (officer_id) REFERENCES officers (id) ON DELETE CASCADE,
    FOREIGN KEY (incident_id) REFERENCES incidents (id) ON DELETE CASCADE,
    UNIQUE(officer_id, incident_id)
);

-- ── 5. Notification queue table: tracks SMS/call notifications to officers ────
CREATE TABLE IF NOT EXISTS notification_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    officer_assignment_id INTEGER NOT NULL,
    notification_type VARCHAR NOT NULL,
    phone_number VARCHAR NOT NULL,
    message_body TEXT NOT NULL,
    twilio_sid VARCHAR,
    status VARCHAR DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sent_at DATETIME,
    failed_at DATETIME,
    FOREIGN KEY (officer_assignment_id) REFERENCES officer_assignments (id) ON DELETE CASCADE
);

-- ── 6. Create indexes for performance ────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_incidents_dispatch_status ON incidents (dispatch_status);
CREATE INDEX IF NOT EXISTS idx_incidents_assigned_officer_id ON incidents (assigned_officer_id);
CREATE INDEX IF NOT EXISTS idx_incidents_assigned_department ON incidents (assigned_department);
CREATE INDEX IF NOT EXISTS idx_officers_department ON officers (department);
CREATE INDEX IF NOT EXISTS idx_officers_status ON officers (status);
CREATE INDEX IF NOT EXISTS idx_dispatch_logs_incident_id ON dispatch_logs (incident_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_logs_timestamp ON dispatch_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_officer_assignments_officer_id ON officer_assignments (officer_id);
CREATE INDEX IF NOT EXISTS idx_notification_queue_status ON notification_queue (status);
CREATE INDEX IF NOT EXISTS idx_officer_assignments_incident_id ON officer_assignments (incident_id);

-- ── 7. Foreign key constraints ───────────────────────────────────────────────
-- Add foreign key for assigned_officer_id to incidents table
-- Note: SQLite doesn't support ADD CONSTRAINT directly, so we rely on triggers/application logic
-- to maintain referential integrity
