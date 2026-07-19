"""
app/utils/trust_score.py

Citizen trust score logic. Extends the existing `devices` table
(which currently only tracks total_reports) with a real trust score
that factors into confidence scoring (see scoring.py) and community
validation weighting.

Schema additions are applied via migrations/schema_updates.sql.
"""

import sqlite3
import os
import datetime

DATABASE_PATH = os.getenv("DATABASE_URL", "sqlite:///instance/roadpulse.db").replace("sqlite:///", "")
if not os.path.dirname(DATABASE_PATH):
    DATABASE_PATH = os.path.join("instance", "roadpulse.db")


def _get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_trust_score(device_id: str) -> float:
    """Return current trust score for a device; neutral 0.5 if unknown."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT trust_score FROM devices WHERE device_id = ?", (device_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return 0.5
    score = row[0]
    return float(score) if score is not None else 0.5


def _compute_score(verified_reports: int, false_reports: int) -> float:
    """
    Simple, explainable blend:
      - accuracy component: verified / (verified + false), defaults to 0.5 with no history
      - volume dampener: new devices should not jump to 1.0 off one good report
    """
    graded = verified_reports + false_reports
    if graded == 0:
        return 0.5

    accuracy = verified_reports / graded
    volume_confidence = min(graded / 10.0, 1.0)  # ramps up to full weight after 10 graded reports
    score = 0.5 + (accuracy - 0.5) * volume_confidence
    return round(max(0.0, min(1.0, score)), 4)


def update_trust_score(device_id: str, was_report_confirmed: bool) -> float:
    """
    Call this whenever an incident report from this device is finally
    resolved (confirmed valid or rejected as false), including outcomes
    driven by community validation consensus.
    """
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT verified_reports, false_reports, total_reports FROM devices WHERE device_id = ?",
        (device_id,),
    )
    row = cur.fetchone()

    if row is None:
        cur.execute(
            "INSERT INTO devices (device_id, total_reports, verified_reports, false_reports, trust_score, last_updated) "
            "VALUES (?, 0, 0, 0, 0.5, ?)",
            (device_id, datetime.datetime.utcnow().isoformat()),
        )
        verified_reports, false_reports = 0, 0
    else:
        verified_reports = row["verified_reports"] or 0
        false_reports = row["false_reports"] or 0

    if was_report_confirmed:
        verified_reports += 1
    else:
        false_reports += 1

    new_score = _compute_score(verified_reports, false_reports)

    cur.execute(
        "UPDATE devices SET verified_reports = ?, false_reports = ?, trust_score = ?, last_updated = ? "
        "WHERE device_id = ?",
        (verified_reports, false_reports, new_score, datetime.datetime.utcnow().isoformat(), device_id),
    )
    conn.commit()
    conn.close()
    return new_score


def apply_validation_vote_outcome(device_id: str, voted_with_consensus: bool) -> float:
    """
    Adjusts trust score for a device that *validated* (not authored) a report,
    based on whether their vote matched the eventual consensus outcome.
    """
    return update_trust_score(device_id, was_report_confirmed=voted_with_consensus)


def get_trust_breakdown(device_id: str) -> dict:
    """Return full trust breakdown for the /devices/<id>/trust endpoint."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT device_id, trust_score, verified_reports, false_reports, total_reports, last_updated "
        "FROM devices WHERE device_id = ?",
        (device_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return {
            "device_id": device_id,
            "trust_score": 0.5,
            "verified_reports": 0,
            "false_reports": 0,
            "total_reports": 0,
            "last_updated": None,
        }
    return dict(row)
