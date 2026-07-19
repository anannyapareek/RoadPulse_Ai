"""
app/integrations/emergency_call.py

Emergency Call integration using Twilio + Gemini voice.
Adapted from the Twilio birthday-call sample pattern (same /voice -> /listen
webhook loop), repointed at incident reporting.

Trigger condition: high-severity incident type + high confidence score.
All credentials are read from environment variables — never hard-coded.

Register with:
    from app.integrations.emergency_call import emergency_bp, trigger_emergency_call
    app.register_blueprint(emergency_bp)

Call trigger_emergency_call() from app.py after an incident finishes scoring.
"""

import os
import datetime
from flask import Blueprint, request

from app.db import execute_db, query_db

# ─── Guard: only import Twilio/Gemini SDKs when env vars are present ──────────
try:
    from twilio.rest import Client as TwilioClient
    from twilio.twiml.voice_response import VoiceResponse
    _TWILIO_AVAILABLE = True
except ImportError:
    _TWILIO_AVAILABLE = False

try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

# ─── Config ───────────────────────────────────────────────────────
HIGH_SEVERITY_TYPES = {"accident", "flooding", "signal_outage"}
CONFIDENCE_THRESHOLD = float(os.getenv("EMERGENCY_CONFIDENCE_THRESHOLD", "0.8"))
VALID_TWILIO_VOICE = "Google.en-US-Neural2-F"
SPEECH_RECOGNITION_LANG = "en-US"
GEMINI_MODEL = "gemini-2.0-flash"

SYSTEM_INSTRUCTION = (
    "You are an automated road-incident notification assistant calling on behalf "
    "of the RoadPulse city monitoring system. "
    "STRICT RULES: "
    "1. State the incident type, approximate location, and confidence level clearly. "
    "2. Keep the tone calm, factual, and brief -- this is an operational alert, not a chat. "
    "3. If asked for more detail, restate the same facts; don't speculate. "
    "4. Do not ask unrelated questions."
)

emergency_bp = Blueprint("emergency_call", __name__)
_twilio_client = None
_gemini_client = None
_active_calls: dict = {}  # call_sid -> incident_id (fine for single-process deployments)


def _twilio():
    global _twilio_client
    if _twilio_client is None and _TWILIO_AVAILABLE:
        _twilio_client = TwilioClient(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN"),
        )
    return _twilio_client


def _gemini_chat():
    global _gemini_client
    if _gemini_client is None and _GENAI_AVAILABLE:
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    if _gemini_client is None:
        return None
    return _gemini_client.chats.create(
        model=GEMINI_MODEL,
        config=genai_types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
    )


def _log_call(incident_id: int, call_sid: str, status: str):
    execute_db(
        "INSERT INTO emergency_calls (incident_id, call_sid, status, timestamp) VALUES (?, ?, ?, ?)",
        (incident_id, call_sid, status, datetime.datetime.utcnow().isoformat()),
    )


def should_trigger_emergency_call(incident_type: str, confidence_score: float) -> bool:
    return incident_type in HIGH_SEVERITY_TYPES and confidence_score >= CONFIDENCE_THRESHOLD


def trigger_emergency_call(
    incident_id: int,
    incident_type: str,
    location_desc: str,
    confidence_score: float,
) -> str | None:
    """
    Call this after an incident is scored. Fires a Twilio call if it meets
    the severity + confidence threshold. No-op otherwise.
    Returns the call SID or None.
    """
    if not should_trigger_emergency_call(incident_type, confidence_score):
        return None

    if not _TWILIO_AVAILABLE:
        print("[emergency_call] Twilio SDK not installed -- skipping call.")
        return None

    ngrok_url = os.getenv("NGROK_URL")
    to_number = os.getenv("EMERGENCY_CONTACT_NUMBER")
    twilio_number = os.getenv("TWILIO_NUMBER")

    if not all([ngrok_url, to_number, twilio_number]):
        print("[emergency_call] Missing NGROK_URL / EMERGENCY_CONTACT_NUMBER / TWILIO_NUMBER -- skipping call.")
        return None

    try:
        call = _twilio().calls.create(
            url=f"{ngrok_url}/voice?incident_id={incident_id}",
            to=to_number,
            from_=twilio_number,
        )
        _active_calls[call.sid] = incident_id
        _log_call(incident_id, call.sid, "initiated")
        return call.sid
    except Exception as e:
        _log_call(incident_id, "N/A", f"failed: {e}")
        return None


# ─── Twilio Webhook Endpoints ──────────────────────────────────────

@emergency_bp.route("/voice", methods=["POST"])
def voice():
    if not _TWILIO_AVAILABLE:
        return "Twilio not configured", 500

    incident_id = request.args.get("incident_id")
    resp = VoiceResponse()

    row = query_db(
        "SELECT incident_type, notes, confidence_score FROM incidents WHERE id = ?",
        (incident_id,),
        one=True,
    )

    if row:
        incident_type = row["incident_type"]
        location_desc = row["notes"] or "unknown location"
        confidence = row["confidence_score"]
        greeting = (
            f"RoadPulse alert. A {incident_type} incident was reported near {location_desc}, "
            f"with {round(confidence * 100)} percent confidence. "
            f"Please take appropriate action."
        )
    else:
        greeting = "RoadPulse alert. An incident was reported, but details could not be retrieved."

    resp.say(greeting, voice=VALID_TWILIO_VOICE, language=SPEECH_RECOGNITION_LANG)
    resp.gather(
        input="speech",
        action=f"/listen?incident_id={incident_id}",
        timeout=5,
        speech_timeout="auto",
        language=SPEECH_RECOGNITION_LANG,
    )
    return str(resp)


@emergency_bp.route("/listen", methods=["POST"])
def listen():
    if not _TWILIO_AVAILABLE:
        return "Twilio not configured", 500

    incident_id = request.args.get("incident_id")
    user_text = request.values.get("SpeechResult", "")
    resp = VoiceResponse()

    if not user_text:
        resp.say("I didn't hear anything. Could you repeat that?", voice=VALID_TWILIO_VOICE)
        resp.gather(input="speech", action=f"/listen?incident_id={incident_id}", timeout=5)
        return str(resp)

    if any(phrase in user_text.lower() for phrase in ["goodbye", "hang up", "bye", "acknowledged"]):
        resp.say("Understood, ending call. Goodbye.", voice=VALID_TWILIO_VOICE)
        resp.hangup()
        return str(resp)

    chat = _gemini_chat()
    if chat:
        try:
            ai_response = chat.send_message(user_text)
            ai_text = ai_response.text.strip()
        except Exception:
            ai_text = "I'm sorry, I missed that. Can you say it again?"
    else:
        ai_text = "AI assistant is not available right now."

    resp.say(ai_text, voice=VALID_TWILIO_VOICE, language=SPEECH_RECOGNITION_LANG)
    resp.gather(input="speech", action=f"/listen?incident_id={incident_id}", timeout=5)
    return str(resp)
