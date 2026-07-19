"""
app/routes/community_validation.py

Community Validation endpoints: public confirm/reject votes on existing
incidents, plus additional-photo upload. Feeds back into both the
confidence model (as a feature, once you retrain on it) and the citizen
trust score of the voting device.

Register with:
    from app.routes.community_validation import validation_bp
    app.register_blueprint(validation_bp)
"""

import os
import datetime
from flask import Blueprint, request, jsonify

from app.db import get_db, execute_db, query_db
from app.utils.trust_score import apply_validation_vote_outcome

CONSENSUS_THRESHOLD = 3  # min votes before a consensus outcome is locked in
UPLOAD_FOLDER = "uploads/incidents"

validation_bp = Blueprint("community_validation", __name__)


@validation_bp.route("/incidents/<int:incident_id>/validate", methods=["POST"])
def validate_incident(incident_id):
    """
    Body: {"device_id": "...", "vote": "confirm"|"reject", "note": "..."}
    Records one vote per device per incident. On reaching CONSENSUS_THRESHOLD,
    updates the incident status and adjusts every voter's trust score.
    """
    data = request.json or {}
    device_id = data.get("device_id")
    vote = data.get("vote")
    note = data.get("note")

    if vote not in ("confirm", "reject"):
        return jsonify({"error": "vote must be 'confirm' or 'reject'"}), 400
    if not device_id:
        return jsonify({"error": "device_id is required"}), 400

    # Ensure incident exists
    incident = query_db("SELECT id, status FROM incidents WHERE id = ?", (incident_id,), one=True)
    if incident is None:
        return jsonify({"error": "Incident not found"}), 404

    # Insert vote (UNIQUE constraint blocks double-voting)
    try:
        execute_db(
            "INSERT INTO incident_validations (incident_id, device_id, vote, note, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (incident_id, device_id, vote, note, datetime.datetime.utcnow().isoformat()),
        )
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return jsonify({"error": "This device has already voted on this incident"}), 409
        raise

    # Tally votes
    rows = query_db(
        "SELECT vote, COUNT(*) as c FROM incident_validations WHERE incident_id = ? GROUP BY vote",
        (incident_id,),
    )
    tally = {row["vote"]: row["c"] for row in rows}
    total_votes = sum(tally.values())

    consensus_reached = False
    consensus_outcome = None

    if total_votes >= CONSENSUS_THRESHOLD:
        confirm_votes = tally.get("confirm", 0)
        reject_votes = tally.get("reject", 0)
        if confirm_votes != reject_votes:
            consensus_outcome = "confirm" if confirm_votes > reject_votes else "reject"
            consensus_reached = True

            new_status = "CONFIRMED" if consensus_outcome == "confirm" else "REJECTED"
            execute_db(
                "UPDATE incidents SET status = ? WHERE id = ?",
                (new_status, incident_id),
            )

            # Adjust trust score for every voter based on agreement with consensus
            voters = query_db(
                "SELECT device_id, vote FROM incident_validations WHERE incident_id = ?",
                (incident_id,),
            )
            for row in voters:
                agreed = row["vote"] == consensus_outcome
                apply_validation_vote_outcome(row["device_id"], agreed)

    return jsonify({
        "incident_id": incident_id,
        "vote_recorded": vote,
        "current_tally": tally,
        "consensus_reached": consensus_reached,
        "consensus_outcome": consensus_outcome,
    })


@validation_bp.route("/incidents/<int:incident_id>/photos", methods=["POST"])
def add_incident_photo(incident_id):
    """
    Accepts an additional photo for an existing incident.
    Expects multipart/form-data with a 'photo' file field.
    Runs the new photo through the existing Gemini image-validation
    pipeline before attaching it.
    """
    from app.services.gemini_service import classify_image

    incident = query_db("SELECT id FROM incidents WHERE id = ?", (incident_id,), one=True)
    if incident is None:
        return jsonify({"error": "Incident not found"}), 404

    if "photo" not in request.files:
        return jsonify({"error": "photo file is required"}), 400

    photo = request.files["photo"]

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ts = datetime.datetime.utcnow().timestamp()
    saved_path = os.path.join(UPLOAD_FOLDER, f"{incident_id}_{ts}.jpg")
    photo.save(saved_path)

    # Validate via the same Gemini pipeline used for primary reports
    try:
        classification, _ = classify_image(saved_path)
        is_valid = classification.get("confidence_score", 0) >= 0.3
        reason = classification.get("reason", "")
    except Exception as e:
        is_valid = False
        reason = str(e)

    if not is_valid:
        return jsonify({"error": f"Photo rejected by AI validation: {reason}"}), 422

    execute_db(
        "INSERT INTO incident_photos (incident_id, file_path, uploaded_at) VALUES (?, ?, ?)",
        (incident_id, saved_path, datetime.datetime.utcnow().isoformat()),
    )

    return jsonify({
        "incident_id": incident_id,
        "photo_path": saved_path,
        "validation": {"valid": is_valid, "reason": reason},
    })
