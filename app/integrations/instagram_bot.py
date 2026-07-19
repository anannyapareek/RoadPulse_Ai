"""
app/integrations/instagram_bot.py

Instagram Reporting channel. Adapted from the instagrapi DM-bot pattern
(session state machine, JSON-extraction via LLM, media validation).
Repointed from food orders / MySQL to RoadPulse incident reports / SQLite.
Images are routed through the same Gemini validation pipeline used by app.py.

Credentials are read from environment variables -- never hard-coded.

Run modes:
    python -m app.integrations.instagram_bot              -> bot loop
    python -m app.integrations.instagram_bot @handle msg -> CLI single DM
"""

import os
import sys
import time
import json
import datetime
from pathlib import Path

# ─── Guard optional deps ──────────────────────────────────────────
try:
    from instagrapi import Client as InstaClient
    _INSTA_AVAILABLE = True
except ImportError:
    _INSTA_AVAILABLE = False

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

from app.utils.scoring import predict_confidence, encode_incident_type
from app.utils.trust_score import get_trust_score
from app.db import get_db, execute_db, query_db

# ─── Config (env vars) ───────────────────────────────────────────
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SESSION_FILE = Path(__file__).parent / "instagram_session.json"

INCIDENT_TYPES = ["pothole", "accident", "flooding", "debris", "signal_outage", "crack", "congestion", "other"]

if _OPENAI_AVAILABLE and GROQ_API_KEY:
    groq = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    GROQ_MODEL = "llama-3.3-70b-versatile"
else:
    groq = None
    GROQ_MODEL = None


# ─── DB helpers ──────────────────────────────────────────────────

def _get_or_create_device_id(insta_username: str) -> str:
    """Look up or create a device_id for an Instagram handle."""
    row = query_db(
        "SELECT device_id FROM device_socials WHERE handle = ? AND platform = 'instagram'",
        (insta_username,),
        one=True,
    )
    if row:
        return row["device_id"]
    device_id = f"ig:{insta_username}"
    execute_db(
        "INSERT OR IGNORE INTO device_socials (device_id, handle, platform) VALUES (?, ?, 'instagram')",
        (device_id, insta_username),
    )
    return device_id


def save_incident_from_instagram(insta_username: str, state: dict) -> tuple[int, float]:
    """Write a completed Instagram-sourced incident into the RoadPulse incidents table."""
    device_id = _get_or_create_device_id(insta_username)
    trust = get_trust_score(device_id)
    incident_type = state.get("incident_type", "other")
    incident_type_code = encode_incident_type(incident_type)

    confidence = predict_confidence({
        "base_score": 1.0,
        "gps_accuracy_factor": 0.7,      # Instagram reports have no GPS; use conservative factor
        "duplicate_factor": 1.0,
        "device_trust_score": trust,
        "hour_of_day": datetime.datetime.utcnow().hour,
        "image_validation_passed": 1.0 if state.get("image_validated") else 0.0,
        "incident_type_code": incident_type_code,
    })

    incident_id = execute_db(
        "INSERT INTO incidents "
        "(device_id, latitude, longitude, gps_accuracy, incident_type, severity_level, "
        "confidence_score, notes, is_duplicate) "
        "VALUES (?, 0.0, 0.0, 999.0, ?, 'medium', ?, ?, 0)",
        (
            device_id,
            incident_type,
            round(confidence, 4),
            state.get("location", ""),
        ),
    )
    return incident_id, confidence


# ─── LLM Conversation ────────────────────────────────────────────

def _build_system_prompt() -> str:
    types_text = ", ".join(INCIDENT_TYPES)
    return f"""You are a RoadPulse incident-reporting assistant on Instagram DM.
Keep replies SHORT (max 2 sentences).

Valid incident types: {types_text}

Rules:
- Collect: incident_type (must be one of the valid types), location (text description),
  and encourage a photo if none was sent yet
- NEVER re-ask for info already given
- Ask ONLY ONE question at a time
- Once incident_type and location are collected, confirm and thank the reporter

Always respond ONLY in this JSON format:
{{
  "reply": "short Instagram-style reply here",
  "extracted": {{
    "incident_type": "...",
    "location": "..."
  }}
}}
Only include fields in "extracted" that were just mentioned. Use null for fields not mentioned."""


def _get_missing(state: dict) -> list[str]:
    missing = []
    if not state.get("incident_type"):
        missing.append("incident type")
    if not state.get("location"):
        missing.append("location")
    return missing


def _update_state(state: dict, extracted: dict) -> dict:
    if extracted.get("incident_type"):
        state["incident_type"] = extracted["incident_type"]
    if extracted.get("location"):
        state["location"] = extracted["location"]
    return state


def _clean_reply(text: str) -> str:
    if "{" in text:
        text = text[:text.index("{")].strip()
    return text.strip()


def process_message(user_input: str, history: list, state: dict, system_prompt: str):
    if groq is None:
        return "Sorry, the AI assistant is not available right now.", history, state, False

    history.append({"role": "user", "content": user_input})
    messages = [{"role": "system", "content": system_prompt}] + history
    messages.append({
        "role": "system",
        "content": f"Current report: {json.dumps(state)}\nStill missing: {_get_missing(state)}",
    })

    try:
        response = groq.chat.completions.create(model=GROQ_MODEL, messages=messages, temperature=0.4)
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        parsed = json.loads(raw.strip())
        reply = _clean_reply(parsed.get("reply", "Got it 👍"))
        extracted = parsed.get("extracted", {})
        if extracted:
            state = _update_state(state, extracted)

        history.append({"role": "assistant", "content": reply})
        is_complete = len(_get_missing(state)) == 0
        return reply, history, state, is_complete

    except json.JSONDecodeError:
        fallback = _clean_reply(raw) if "raw" in dir() else "Sorry, could you say that again?"
        history.append({"role": "assistant", "content": fallback})
        return fallback, history, state, False
    except Exception as e:
        return f"Sorry, something went wrong: {e}", history, state, False


def analyze_and_validate_media(url: str, media_type: str = "image") -> tuple[str, bool]:
    """
    Routes the image through the same Gemini validation pipeline used by app.py
    instead of a generic reaction.
    """
    from app.services.gemini_service import classify_image
    try:
        classification, _ = classify_image(url)
        is_valid = classification.get("confidence_score", 0) >= 0.3
        reason = classification.get("reason", "")
        if is_valid:
            reaction = "Got the photo, thanks — that helps confirm the report. 📸"
        else:
            reaction = f"That image couldn't be used ({reason or 'unclear photo'}) — got another one?"
        return reaction, is_valid
    except Exception as e:
        return f"Couldn't process the image: {e}", False


# ─── Instagram Login ─────────────────────────────────────────────

def instagram_login():
    if not _INSTA_AVAILABLE:
        print("❌ instagrapi not installed -- run: pip install instagrapi")
        return None

    cl = InstaClient()
    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            cl.get_timeline_feed()
            print(f"✅ Logged in via saved session as {INSTAGRAM_USERNAME}")
            return cl
        except Exception as e:
            print(f"⚠️ Saved session invalid ({e}), logging in fresh...")
            SESSION_FILE.unlink(missing_ok=True)

    try:
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        cl.dump_settings(SESSION_FILE)
        print(f"✅ Fresh login successful, session saved to {SESSION_FILE}")
        return cl
    except Exception as e:
        print(f"❌ Instagram login failed: {e}")
        return None


# ─── Bot Loop ────────────────────────────────────────────────────

def run_instagram_bot():
    cl = instagram_login()
    if not cl:
        return

    system_prompt = _build_system_prompt()
    user_sessions: dict = {}
    thread_last_seen: dict = {}

    print("\n📱 Listening for Instagram DMs (incident reports)...\n")

    while True:
        try:
            threads = cl.direct_threads()
            for thread in threads:
                if not thread.messages:
                    continue
                msg = thread.messages[0]
                thread_id = thread.id
                if thread_last_seen.get(thread_id) == msg.id:
                    continue

                user_id = str(msg.user_id)
                username = cl.user_info(msg.user_id).username
                if username == INSTAGRAM_USERNAME:
                    thread_last_seen[thread_id] = msg.id
                    continue

                if user_id not in user_sessions:
                    user_sessions[user_id] = {
                        "history": [],
                        "state": {"incident_type": None, "location": None, "image_validated": False},
                    }

                session = user_sessions[user_id]

                if msg.text:
                    reply, session["history"], session["state"], is_complete = process_message(
                        msg.text, session["history"], session["state"], system_prompt
                    )
                    cl.direct_send(reply, [msg.user_id])

                    if is_complete:
                        incident_id, confidence = save_incident_from_instagram(username, session["state"])
                        confirm = f"✅ Report #{incident_id} logged (confidence {round(confidence * 100)}%). Thanks for reporting!"
                        cl.direct_send(confirm, [msg.user_id])
                        del user_sessions[user_id]
                else:
                    media_to_process = []
                    if msg.media:
                        media_to_process = msg.media if isinstance(msg.media, list) else [msg.media]
                    if hasattr(msg, "media_share") and msg.media_share:
                        media_to_process.append(msg.media_share)
                    for m in media_to_process:
                        url = getattr(m, "thumbnail_url", getattr(m, "url", None))
                        if url:
                            mt = getattr(m, "media_type", 1)
                            media_type_str = "image" if mt == 1 else "video"
                            reaction, is_valid = analyze_and_validate_media(url, media_type_str)
                            session["state"]["image_validated"] = is_valid
                            cl.direct_send(reaction, [msg.user_id])

                thread_last_seen[thread_id] = msg.id

        except Exception as e:
            err_msg = str(e).lower()
            if any(x in err_msg for x in ["challenge", "checkpoint", "404", "login_required"]):
                print(f"❌ Instagram Challenge/Auth Error: {e}")
                print("⌛ Backing off for 5 minutes...")
                time.sleep(300)
            else:
                print(f"⚠️ Loop error: {e}")
                time.sleep(10)

        time.sleep(5)


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        target_handle = sys.argv[1].replace("@", "")
        dm_message = sys.argv[2]
        cl = instagram_login()
        if cl:
            try:
                target_user_id = cl.user_id_from_username(target_handle)
                cl.direct_send(dm_message, [target_user_id])
                print(f"✅ DM sent to @{target_handle}: {dm_message}")
            except Exception as e:
                print(f"❌ Failed to send DM to @{target_handle}: {e}")
        else:
            print("❌ Instagram login failed — DM not sent.")
    else:
        run_instagram_bot()
