"""
app/routes/dashboard.py

Login-based dashboard routing + the User dashboard (citizen view of their
own reports) and data feed for the existing Admin dashboard.

Routing logic, per spec: "predict it using AI only, because it depends on
too many factors" -- implemented as an AI tie-breaker for AMBIGUOUS accounts
only. A hard is_admin flag, when present, always wins; Gemini is only
consulted when that flag is missing/unclear.

Register with:
    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
"""

import os
import json
import datetime
from flask import Blueprint, request, jsonify
from google import genai

from app.db import get_db, execute_db, query_db
from app.utils.trust_score import get_trust_breakdown

GEMINI_MODEL = "gemini-2.0-flash"

dashboard_bp = Blueprint("dashboard", __name__)
_gemini_client = None


def _client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


def _gather_login_signals(user_id: str) -> dict:
    row = query_db(
        "SELECT is_admin, total_reports, trust_score, admin_actions_count "
        "FROM users WHERE user_id = ?",
        (user_id,),
        one=True,
    )
    if row is None:
        return {}
    return dict(row)


def _ai_route_decision(signals: dict) -> dict:
    """
    Only called for ambiguous accounts (is_admin is NULL). Logs the
    reasoning for audit purposes. NEVER overrides an explicit is_admin flag.
    """
    prompt = (
        f"A user is logging into RoadPulse with these account signals: {signals}. "
        f"Decide whether this session should land on the 'admin' or 'user' dashboard. "
        f"Default to 'user' unless there's clear evidence of admin-level activity "
        f"(e.g. a meaningful admin_actions_count). Respond ONLY with JSON: "
        f'{{"destination": "admin"|"user", "reasoning": "<one sentence>"}}'
    )
    try:
        response = _client().models.generate_content(model=GEMINI_MODEL, contents=prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        # Fail-safe: lower-privilege destination
        return {"destination": "user", "reasoning": "AI response unavailable; defaulted to user for safety."}


def _log_routing_decision(user_id: str, destination: str, reasoning: str, source: str):
    execute_db(
        "INSERT INTO dashboard_routing_log (user_id, destination, reasoning, source, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, destination, reasoning, source, datetime.datetime.utcnow().isoformat()),
    )


def route_login_destination(user_id: str) -> dict:
    signals = _gather_login_signals(user_id)

    is_admin_flag = signals.get("is_admin")
    if is_admin_flag is not None:
        # Hard flag always wins
        destination = "admin" if bool(is_admin_flag) else "user"
        _log_routing_decision(user_id, destination, "Explicit is_admin flag", source="flag")
        return {"destination": destination, "reasoning": "Explicit account flag", "source": "flag"}

    # Ambiguous account: consult AI as tie-breaker only
    decision = _ai_route_decision(signals)
    _log_routing_decision(user_id, decision["destination"], decision.get("reasoning", ""), source="ai_tiebreak")
    return {**decision, "source": "ai_tiebreak"}


# ─── Endpoints ────────────────────────────────────────────────────

@dashboard_bp.route("/login/route", methods=["POST"])
def login_route():
    data = request.json or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    result = route_login_destination(user_id)
    return jsonify(result)


@dashboard_bp.route("/dashboard/user/<user_id>/reports", methods=["GET"])
def user_reports(user_id):
    """Citizen dashboard: pending / resolved / rejected reports for this user's device(s)."""
    rows = query_db(
        "SELECT id, incident_type, notes, status, confidence_score, created_at, latitude, longitude "
        "FROM incidents WHERE device_id IN "
        "(SELECT device_id FROM device_socials WHERE user_id = ? UNION SELECT ?) "
        "ORDER BY created_at DESC",
        (user_id, user_id),
    )
    grouped = {"pending": [], "resolved": [], "rejected": []}
    for r in rows:
        row_dict = dict(r)
        status = (row_dict.get("status") or "PENDING").upper()
        if status == "CONFIRMED":
            grouped["resolved"].append(row_dict)
        elif status == "REJECTED":
            grouped["rejected"].append(row_dict)
        else:
            grouped["pending"].append(row_dict)

    return jsonify(grouped)


@dashboard_bp.route("/devices/<device_id>/trust", methods=["GET"])
def device_trust(device_id):
    """Return current trust score + breakdown for a device."""
    breakdown = get_trust_breakdown(device_id)
    return jsonify(breakdown)


@dashboard_bp.route("/summaries", methods=["GET"])
def get_summaries():
    """GET /summaries?period=daily|weekly|monthly — returns the latest stored summary."""
    period = request.args.get("period", "daily")
    if period not in ("daily", "weekly", "monthly"):
        return jsonify({"error": "period must be daily, weekly, or monthly"}), 400

    row = query_db(
        "SELECT period_type, period_start, period_end, summary_text, generated_at "
        "FROM summaries WHERE period_type = ? ORDER BY generated_at DESC LIMIT 1",
        (period,),
        one=True,
    )
    if row is None:
        return jsonify({"error": f"No {period} summary generated yet"}), 404
    return jsonify(dict(row))
