"""
app/utils/knowledge_db.py

AI Knowledge Database & Executive Summaries.
Aggregates incident data on a schedule (daily/weekly/monthly) and asks
Gemini to produce an executive summary, storing the result in the
`summaries` table so the admin dashboard can pull it via GET /summaries.

Schema addition applied via migrations/schema_updates.sql.

Start the scheduler at app startup:
    from app.utils.knowledge_db import start_scheduler
    start_scheduler()
"""

import os
import sqlite3
import datetime

DATABASE_PATH = os.getenv("DATABASE_URL", "sqlite:///instance/roadpulse.db").replace("sqlite:///", "")
if not os.path.dirname(DATABASE_PATH):
    DATABASE_PATH = os.path.join("instance", "roadpulse.db")

GEMINI_MODEL = "gemini-2.0-flash"

_gemini_client = None


def _client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


def _get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _period_bounds(period_type: str) -> tuple[str, str]:
    now = datetime.datetime.utcnow()
    if period_type == "daily":
        start = now - datetime.timedelta(days=1)
    elif period_type == "weekly":
        start = now - datetime.timedelta(weeks=1)
    elif period_type == "monthly":
        start = now - datetime.timedelta(days=30)
    else:
        raise ValueError("period_type must be daily, weekly, or monthly")
    return start.isoformat(), now.isoformat()


def _fetch_aggregates(period_start: str, period_end: str) -> dict:
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT incident_type, COUNT(*) as cnt FROM incidents "
        "WHERE created_at BETWEEN ? AND ? GROUP BY incident_type",
        (period_start, period_end),
    )
    by_type = {row[0]: row[1] for row in cur.fetchall()}

    cur.execute(
        "SELECT COUNT(*) FROM incidents WHERE created_at BETWEEN ? AND ?",
        (period_start, period_end),
    )
    total = cur.fetchone()[0]

    cur.execute(
        "SELECT AVG(confidence_score) FROM incidents WHERE created_at BETWEEN ? AND ?",
        (period_start, period_end),
    )
    avg_confidence = cur.fetchone()[0] or 0.0

    cur.execute(
        "SELECT COUNT(*) FROM incidents WHERE is_duplicate = 1 AND created_at BETWEEN ? AND ?",
        (period_start, period_end),
    )
    duplicates = cur.fetchone()[0]

    conn.close()
    return {
        "total_incidents": total,
        "by_type": by_type,
        "avg_confidence": round(avg_confidence, 3),
        "duplicates_merged": duplicates,
    }


def _generate_summary_text(period_type: str, aggregates: dict) -> str:
    prompt = (
        f"Write a concise executive summary (4-6 sentences) for road-incident "
        f"reporting activity over the past {period_type} period, for a city "
        f"operations team. Data: {aggregates}. "
        f"Highlight the most frequent incident type, any notable volume changes "
        f"implied by the numbers, duplicate merges as a quality signal, "
        f"and overall data confidence. Plain text only."
    )
    try:
        response = _client().models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"[Summary generation failed: {e}]"


def generate_summary(period_type: str) -> dict:
    """Generate and persist an executive summary for the given period."""
    period_start, period_end = _period_bounds(period_type)
    aggregates = _fetch_aggregates(period_start, period_end)
    summary_text = _generate_summary_text(period_type, aggregates)

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO summaries (period_type, period_start, period_end, summary_text, generated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (period_type, period_start, period_end, summary_text, datetime.datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    return {
        "period_type": period_type,
        "period_start": period_start,
        "period_end": period_end,
        "summary_text": summary_text,
        "aggregates": aggregates,
    }


def get_latest_summary(period_type: str) -> dict | None:
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT period_type, period_start, period_end, summary_text, generated_at "
        "FROM summaries WHERE period_type = ? ORDER BY generated_at DESC LIMIT 1",
        (period_type,),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def start_scheduler():
    """
    Call once at app startup to begin scheduled summary generation.
    Requires: pip install apscheduler
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        print("[knowledge_db] APScheduler not installed -- scheduled summaries disabled. "
              "Run: pip install apscheduler")
        return None

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(lambda: generate_summary("daily"), "cron", hour=1, minute=0)
    scheduler.add_job(lambda: generate_summary("weekly"), "cron", day_of_week="mon", hour=1, minute=30)
    scheduler.add_job(lambda: generate_summary("monthly"), "cron", day=1, hour=2, minute=0)
    scheduler.start()
    print("[knowledge_db] Scheduler started: daily(01:00), weekly(Mon 01:30), monthly(1st 02:00) UTC")
    return scheduler
