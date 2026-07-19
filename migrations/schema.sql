-- RoadPulse AI Database Schema

-- Incidents table: stores reported road issues
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    gps_accuracy REAL DEFAULT 25.0,
    incident_type TEXT NOT NULL,
    severity_level TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    notes TEXT,
    image_filename TEXT,
    raw_gemini_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_duplicate INTEGER DEFAULT 0,
    duplicate_of_id INTEGER,
    FOREIGN KEY (duplicate_of_id) REFERENCES incidents (id) ON DELETE SET NULL
);

-- Device registrations: tracks mobile/user devices
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT UNIQUE NOT NULL,
    device_name TEXT,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_reports INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verified incidents: admin-verified or corrected incidents
CREATE TABLE IF NOT EXISTS verified_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL UNIQUE,
    verified_type TEXT NOT NULL,
    verified_severity TEXT NOT NULL,
    verified_by TEXT,
    verification_notes TEXT,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incidents (id) ON DELETE CASCADE
);

-- Statistics cache: aggregated metrics
CREATE TABLE IF NOT EXISTS statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_key TEXT UNIQUE NOT NULL,
    stat_value TEXT NOT NULL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_incidents_device ON incidents (device_id);
CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents (created_at);
CREATE INDEX IF NOT EXISTS idx_incidents_location ON incidents (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_incidents_type ON incidents (incident_type);
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices (device_id);
