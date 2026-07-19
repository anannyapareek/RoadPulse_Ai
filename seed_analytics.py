import sqlite3
import random
import os
from datetime import datetime, timedelta

DB_PATH = 'instance/roadpulse.db'

def alter_schema(conn):
    cur = conn.cursor()
    # Check if columns exist
    cur.execute("PRAGMA table_info(incidents)")
    columns = [col[1] for col in cur.fetchall()]
    
    if 'status' not in columns:
        print("Adding 'status' column...")
        cur.execute("ALTER TABLE incidents ADD COLUMN status TEXT DEFAULT 'pending'")
    if 'resolved_at' not in columns:
        print("Adding 'resolved_at' column...")
        cur.execute("ALTER TABLE incidents ADD COLUMN resolved_at TIMESTAMP")
    if 'ward' not in columns:
        print("Adding 'ward' column...")
        cur.execute("ALTER TABLE incidents ADD COLUMN ward TEXT")
    
    conn.commit()

def seed_data(conn):
    cur = conn.cursor()
    
    # We will insert 20 historical incidents
    now = datetime.utcnow()
    wards = ['Ward 1 (North)', 'Ward 2 (South)', 'Ward 3 (East)', 'Ward 4 (West)', 'Ward 5 (Central)']
    types = ['pothole', 'waterlogging', 'accident', 'signal_failure', 'blocked_road']
    
    for i in range(20):
        # 5 of them will be > 60 days old and pending
        if i < 5:
            created_at = now - timedelta(days=random.randint(65, 90))
            status = 'pending'
            resolved_at = None
        else:
            # Random mix of resolved and pending for recent ones
            created_at = now - timedelta(days=random.randint(1, 30))
            is_resolved = random.choice([True, False])
            if is_resolved:
                status = 'resolved'
                resolved_at = created_at + timedelta(hours=random.randint(2, 48))
            else:
                status = 'pending'
                resolved_at = None
                
        ward = random.choice(wards)
        inc_type = random.choice(types)
        
        cur.execute('''
            INSERT INTO incidents (
                device_id, latitude, longitude, incident_type, severity_level, confidence_score,
                status, created_at, resolved_at, ward
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"simulated-dev-{i}",
            28.6 + random.random() * 0.1,
            77.2 + random.random() * 0.1,
            inc_type,
            'high',
            0.8 + random.random() * 0.19,
            status,
            created_at.strftime('%Y-%m-%d %H:%M:%S'),
            resolved_at.strftime('%Y-%m-%d %H:%M:%S') if resolved_at else None,
            ward
        ))
        
    # Also update existing incidents to have a random ward and status if they don't have one
    cur.execute("UPDATE incidents SET status = 'pending' WHERE status IS NULL")
    cur.execute("UPDATE incidents SET ward = 'Ward 1 (North)' WHERE ward IS NULL")
    
    conn.commit()
    print("Database seeded with historical analytics data.")

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
    else:
        conn = sqlite3.connect(DB_PATH)
        alter_schema(conn)
        seed_data(conn)
        conn.close()
