# RoadPulse AI — One-Day Hackathon Implementation Report

**Scope:** This report replaces the 21-section "national smart-city" architecture with a version you can actually finish in one day and demo convincingly. Every section maps a piece of the original vision onto a real, buildable component — using **Flask + plain HTML/CSS/JS + Leaflet + OpenStreetMap + the Gemini API** — and is explicit about what's simulated, simplified, or deferred, so you can defend every design choice to a judge.

---

## 0. Reality Check — What Changed and Why

The original spec asked for CLIP embeddings, DBSCAN clustering, XGBoost severity/confidence models, SHAP + Grad-CAM explainability, LSTM risk forecasting, a knowledge graph, and a multi-agent orchestration layer. None of that is buildable *and trainable* in one day — you have no labeled dataset, no time to train anything, and no GPU pipeline. Judges at good hackathons penalize teams whose architecture diagrams promise things the demo doesn't back up.

The move that actually wins: **replace every "train a custom model" step with a single well-prompted multimodal LLM call (Gemini)**, and be upfront about that substitution. It's a legitimate, current architectural pattern (structured-output LLM calls instead of bespoke classifiers) — not a shortcut you have to hide.

| Original spec component | One-day substitute | Why |
|---|---|---|
| YOLOv11 / RT-DETR fine-tuned detector | Gemini multimodal call with structured JSON output | Zero training data, zero training time |
| CLIP embeddings + DBSCAN dedup | Haversine distance + type match + time window | Real embeddings need a vector store + tuning; geo+type is 80% of the value for 5% of the effort |
| XGBoost severity/confidence models | Gemini returns severity + confidence directly in the same call | No labeled severity dataset exists yet |
| SHAP + Grad-CAM | Gemini asked to output a short natural-language `reasoning` field | SHAP/Grad-CAM need a custom-trained model you don't have; you're calling a hosted foundation model, so explainability has to come from the model itself, in language |
| LSTM / LightGBM risk forecasting | Rule-based risk score from incident density per grid cell (seeded with synthetic historical data for the demo) | No real historical time series exists on day one |
| KDE heatmap | `Leaflet.heat` weighted by severity | Visually equivalent for a demo; true KDE math documented for the "production roadmap" slide |
| Knowledge graph | Normalized SQLite tables + one `GROUP BY` summary query | A graph DB is solving a problem you don't have yet |
| Multi-agent orchestration (9 agents) | One Flask request pipeline that calls Gemini twice (classify → generate) | "Agents" as separate LLM calls in a pipeline is defensible; a real agent framework (tool loops, memory, planning) is not a one-day build |

Say this explicitly in your pitch: *"We replaced custom-trained CV/ML models with a single foundation-model call because that's the honest, correct engineering tradeoff for a one-day build — and it's also what a lean startup would ship first."* Judges respect that far more than an architecture diagram for models that don't exist.

**On "Gemini open models":** Gemini itself is a *hosted* API (Google AI Studio / `generativelanguage.googleapis.com`), not an open-weight model you self-host — that's what makes it a one-day option (no GPU, no serving infra). If you specifically want open-weight, self-hostable models, Google's **Gemma** family is the open counterpart, but self-hosting adds GPU provisioning, inference server setup, and quantization decisions you don't have time for. **Recommendation: use the hosted Gemini API.** Everything below assumes that.

---

## 1. Final Tech Stack

| Layer | Choice | Why this and not the alternative |
|---|---|---|
| Frontend | Plain HTML + CSS + vanilla JS | No build step, no `npm install` breaking at 2am, judges can open `view-source` and see exactly what you built |
| Map | **Leaflet.js** + `Leaflet.heat` plugin | Free, no API key, no billing account, works offline-ish with OSM tiles, has a mature plugin ecosystem (heatmap, marker clustering, routing display) |
| Map tiles / geocoding | **OpenStreetMap tile server** (for tiles) + **Nominatim** (for address ↔ coordinates) | Free, no signup. **Caveat:** Nominatim's public instance enforces **max 1 request/second** and requires a descriptive `User-Agent` header — fine for a demo, not for production load |
| Routing | **OSRM public demo server** (`router.project-osrm.org`) | Free, no key, returns real road-network routes + alternatives. **Caveat:** demo server policy is "reasonable, non-commercial use only," ~1 req/sec self-throttle recommended, no uptime SLA — perfectly fine for a hackathon demo, explicitly *not* production-grade (call this out on your roadmap slide) |
| Backend | **Flask** (Python) | Minimal boilerplate, one file can be a working API, every teammate already knows it, no auth/ORM ceremony you don't need yet |
| Database | **SQLite** (single file, `roadpulse.db`) | Zero setup, ships with Python, supports everything you need (JSON1 extension available if needed) — swap for Postgres+PostGIS later, not on day one |
| AI — vision + text | **Gemini API**, model `gemini-2.5-flash` | Multimodal (image+text in one call), stable and fully documented, still on the **free tier with rate limits** as of mid-2026, structured JSON output support built in. If your API key has access to `gemini-3-flash-preview` / `gemini-3.1-flash-lite`, those are newer and cheaper for pure classification — but `gemini-2.5-flash` is the safer, better-documented default for a live demo. **Google ships new model versions frequently — check `https://ai.google.dev/gemini-api/docs/models` the morning of the hackathon** and swap the model string if needed; do not hardcode a model that's been deprecated (e.g. `gemini-2.0-flash` was shut down June 1, 2026). |
| Image storage | Local `static/uploads/` folder, path saved in DB | No cloud storage account needed for a demo |
| Hosting for the demo | Run locally on the laptop, phone connects over the venue Wi-Fi to the laptop's LAN IP | Zero deploy risk. Optional: push to Render/Railway free tier as a backup public URL |
| Notifications | Skip real push notifications; simulate with an in-app toast/badge | Push infra (FCM/APNs) is not a one-day item and adds nothing to the demo narrative |
| "Instagram reporting" | Client-side "Share" button that generates a caption + downloads the photo with a watermark overlay, using the Web Share API where available | Real Instagram Graph API posting requires a Meta business app review — not obtainable during a hackathon. Say this plainly if asked |
| Emergency call | Plain `tel:` links (Traffic Police / Ambulance) fired alongside the report submission | Trivial, real, works on any phone, no integration needed |

---

## 2. System Architecture (One-Day Version)

```
                         ┌───────────────────────────┐
                         │   Citizen's Phone/Laptop   │
                         │  (index.html + Leaflet)    │
                         └─────────────┬──────────────┘
                                       │ HTTP (fetch/FormData)
                                       ▼
                         ┌───────────────────────────┐
                         │        Flask App           │
                         │  app.py  /  routes.py      │
                         │                             │
                         │  /api/report   (POST)      │
                         │  /api/incidents(GET)       │
                         │  /api/route    (POST)      │
                         │  /api/stats    (GET)       │
                         │  /admin        (GET, HTML) │
                         └───┬─────────┬──────────┬────┘
                             │         │          │
              ┌──────────────┘         │          └───────────────┐
              ▼                        ▼                          ▼
   ┌─────────────────────┐  ┌──────────────────┐      ┌───────────────────────┐
   │  gemini_service.py   │  │   SQLite DB       │      │  External free APIs   │
   │  - classify_image()  │  │  roadpulse.db     │      │  - Nominatim (geocode)│
   │  - generate_report() │  │  incidents table  │      │  - OSRM (routing)     │
   └──────────┬───────────┘  │  confirmations tbl│      │  - OSM tiles (Leaflet)│
              │              └────────────────────┘      └───────────────────────┘
              ▼
   ┌─────────────────────┐
   │   Gemini API         │
   │ generativelanguage.  │
   │ googleapis.com       │
   └───────────────────────┘
```

**Request flow for a single incident report (this is your whole "AI pipeline" — 8 real steps, not 20 imaginary ones):**

```
1. Browser: navigator.geolocation.getCurrentPosition() → lat, lon
2. Browser: user picks/takes a photo, optional text note
3. Browser: POST multipart/form-data → /api/report (image + lat + lon + note)
4. Flask:   save image to static/uploads/<uuid>.jpg
5. Flask:   call gemini_service.classify_image(image_bytes, note)
              → { type, severity, confidence, is_valid_road_issue, reasoning }
6. Flask:   if is_valid_road_issue == false → reject, return reason to user, STOP
7. Flask:   query SQLite for existing incidents within 50m + same type + last 48h
              → if found: increment confirmations, bump confidence, STOP (duplicate merge)
              → if not found: continue
8. Flask:   compute confidence_score (formula in §5.3), assign department (rule table),
            call gemini_service.generate_report_summary(incident) → LLM-written complaint text
9. Flask:   INSERT into incidents table, return full record (incl. reasoning + summary) to browser
10. Browser: re-fetch /api/incidents, redraw markers + heatmap layer
```

---

## 3. Database Schema (SQLite)

```sql
-- schema.sql

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name  TEXT NOT NULL,
    device_id     TEXT UNIQUE,         -- anonymous device fingerprint, no login needed for MVP
    trust_score   INTEGER DEFAULT 50,
    accepted_reports INTEGER DEFAULT 0,
    rejected_reports INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS incidents (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_type     TEXT NOT NULL,        -- pothole | flooding | accident | construction |
                                             -- blocked_road | broken_signal | fallen_tree | debris
    severity          TEXT NOT NULL,        -- low | medium | high | critical
    confidence_score  REAL NOT NULL,        -- 0.0 - 1.0
    status            TEXT DEFAULT 'pending_review',  -- pending_review | verified | resolved | rejected
    lat               REAL NOT NULL,
    lon               REAL NOT NULL,
    ward              TEXT,
    description_user  TEXT,
    ai_reasoning      TEXT,                 -- Gemini's plain-language explanation
    ai_summary        TEXT,                 -- Gemini-generated complaint text for the department
    department        TEXT,                 -- rule-based routing target
    image_path        TEXT,
    reporter_id       INTEGER REFERENCES users(id),
    confirmations     INTEGER DEFAULT 0,
    duplicate_of      INTEGER REFERENCES incidents(id),  -- NULL if this is the primary report
    created_at        TEXT DEFAULT (datetime('now')),
    resolved_at       TEXT
);

CREATE TABLE IF NOT EXISTS confirmations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id   INTEGER REFERENCES incidents(id),
    user_id       INTEGER REFERENCES users(id),
    vote          TEXT,                 -- confirm | reject
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_incidents_location ON incidents(lat, lon);
CREATE INDEX IF NOT EXISTS idx_incidents_type_status ON incidents(incident_type, status);
```

`lat, lon` as plain REAL columns + a Python haversine check is enough at hackathon scale (hundreds of rows). Don't reach for PostGIS/SpatiaLite on day one — it's real overhead for zero benefit under ~10k rows.

---

## 4. The AI Pipeline in Detail (Gemini)

This is the heart of the report — the part the judges will actually poke at.

### 4.1 Image Classification Call

Ask Gemini for **structured JSON output** directly (a native feature — pass `response_mime_type: "application/json"` with a schema), so you never have to regex-parse free text out of a chat response.

```python
# gemini_service.py
import os, requests, base64, json

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-2.5-flash"
BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

CLASSIFY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_valid_road_issue": {"type": "BOOLEAN"},
        "incident_type": {
            "type": "STRING",
            "enum": ["pothole", "flooding", "accident", "construction",
                     "blocked_road", "broken_signal", "fallen_tree", "debris", "none"]
        },
        "severity": {"type": "STRING", "enum": ["low", "medium", "high", "critical"]},
        "confidence": {"type": "NUMBER"},          # 0.0 - 1.0, model's own certainty
        "reasoning": {"type": "STRING"},           # 1-2 plain-English sentences
        "rejection_reason": {"type": "STRING"}     # filled only if is_valid_road_issue == false
    },
    "required": ["is_valid_road_issue", "incident_type", "severity",
                 "confidence", "reasoning"]
}

CLASSIFY_PROMPT = """You are a road-infrastructure inspector reviewing a citizen-submitted photo.

Determine:
1. Is this genuinely a photo of a road/traffic infrastructure issue (pothole, flooding,
   accident, construction blockage, broken signal, fallen tree, debris)? Reject selfies,
   indoor photos, blank/blurry images, or anything unrelated to roads.
2. If valid, classify the incident type and severity.
   - low: cosmetic, no safety risk
   - medium: noticeable, minor slowdown/discomfort
   - high: real safety or vehicle-damage risk
   - critical: immediate danger (deep pothole, active flooding blocking the road, accident)
3. Give a confidence score (0.0-1.0) for your classification.
4. Give a one-to-two sentence reasoning a citizen or official could read and understand.

Citizen's optional note: "{user_note}"

Respond only in the JSON schema provided."""

def classify_image(image_bytes: bytes, user_note: str = "") -> dict:
    payload = {
        "contents": [{
            "parts": [
                {"text": CLASSIFY_PROMPT.format(user_note=user_note or "none")},
                {"inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(image_bytes).decode("utf-8")
                }}
            ]
        }],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": CLASSIFY_SCHEMA,
            "temperature": 0.2          # low temperature: classification, not creativity
        }
    }
    resp = requests.post(f"{BASE_URL}?key={GEMINI_API_KEY}", json=payload, timeout=20)
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)
```

Why raw `requests` instead of a Google SDK: Google's Python SDK for Gemini has gone through more than one naming/import migration (`google-generativeai` → `google-genai`). The REST endpoint (`generateContent`) has stayed stable across all of that. For a hackathon, a stable REST call you fully control is lower-risk than an SDK whose import path might differ from what a tutorial says. If your team is comfortable with the current SDK, it's a fine swap — just confirm the exact `pip install` and `import` line against `https://ai.google.dev/gemini-api/docs` the morning of the event, since it does change.

### 4.2 Duplicate Detection (geo + type + time, no embeddings)

```python
from math import radians, sin, cos, sqrt, atan2

def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def find_duplicate(db, lat, lon, incident_type, window_hours=48, radius_m=50):
    candidates = db.execute(
        """SELECT * FROM incidents
           WHERE incident_type = ?
             AND duplicate_of IS NULL
             AND created_at >= datetime('now', ?)""",
        (incident_type, f"-{window_hours} hours")
    ).fetchall()
    for row in candidates:
        if haversine_m(lat, lon, row["lat"], row["lon"]) <= radius_m:
            return row
    return None
```

This is the honest substitute for CLIP+DBSCAN: geo-proximity + same category + time window catches the overwhelming majority of real-world duplicates (same pothole reported by five commuters) at a fraction of the engineering cost. State the tradeoff out loud: it will not catch "two different photos of two different potholes on the same street reported as the same type" as *not* duplicate — that's fine, false-merges are rarer than true duplicates in this domain. **Stretch goal**, if time remains: embed each report's `description_user + ai_reasoning` with Gemini's text-embedding model and add a cosine-similarity check on top of the geo filter — but ship the geo-only version first.

### 4.3 Confidence Scoring (rule-based, transparent)

```python
def compute_confidence(gemini_confidence: float, confirmations: int,
                        gps_accuracy_m: float, reporter_trust: int) -> float:
    gps_quality = 1.0 if gps_accuracy_m <= 20 else (0.6 if gps_accuracy_m <= 50 else 0.3)
    confirmation_boost = min(1.0, confirmations / 3)
    trust_factor = min(1.0, reporter_trust / 100)

    score = (0.50 * gemini_confidence +
             0.25 * confirmation_boost +
             0.15 * gps_quality +
             0.10 * trust_factor)
    return round(min(score, 1.0), 3)

VERIFIED_THRESHOLD = 0.55   # tune live during the demo if needed
```

This is deliberately a transparent weighted-sum, not a trained model — which is also *why* it's explainable: you can print the four terms and their weights straight into the UI as the "why" behind a status, and that doubles as your XAI story (see §4.5).

### 4.4 Department Routing (rule table, not ML)

```python
DEPARTMENT_MAP = {
    "pothole":        "Municipal Road Department",
    "flooding":        "Drainage Department",
    "accident":        "Traffic Police",
    "broken_signal":   "Traffic Department",
    "construction":    "Municipal Road Department",
    "blocked_road":    "Traffic Police",
    "fallen_tree":     "Municipal Corporation",
    "debris":          "Municipal Corporation",
}
```

A lookup table is the *correct* engineering choice here, not a corner cut — there's no ambiguity to learn, and a judge who asks "why isn't this ML?" should get "because it's a deterministic mapping, and using ML for a deterministic problem would be worse engineering, not better."

### 4.5 LLM Complaint Generation + Explainability

One more Gemini call, text-only this time, that does double duty: writes the official complaint AND supplies the human-readable explanation.

```python
SUMMARY_PROMPT = """Write a short, professional civic complaint (2-3 sentences) for the
{department} based on this verified incident:

Type: {incident_type}
Severity: {severity}
Location: {lat}, {lon} (Ward: {ward})
Citizen note: {user_note}
AI visual assessment: {reasoning}
Independent confirmations: {confirmations}

Then, separately, write ONE sentence a citizen could read explaining why this report was
accepted and assigned this severity/priority (reference the actual numbers above, e.g.
confidence score, confirmation count, proximity to landmarks if mentioned)."""
```

Return both fields as structured JSON the same way as §4.1 (`complaint_text`, `citizen_explanation`). This is your real, working substitute for the SHAP/Grad-CAM section of the original spec: instead of visualizing feature attributions on a model you don't have, the foundation model is asked to justify itself in language, and your confidence formula (§4.3) is fully transparent by construction. Say this plainly in the demo — "explainability here means every accept/reject decision ships with a human-readable reason, generated from the same signals that produced the decision" — that is a legitimate, defensible XAI claim for an LLM-based system.

---

## 5. Backend Implementation (Flask)

### 5.1 Folder Structure

```
roadpulse/
├── app.py                  # Flask app, route registration
├── gemini_service.py       # classify_image(), generate_report_summary()
├── db.py                   # get_db(), init_db()
├── schema.sql
├── requirements.txt
├── .env                    # GEMINI_API_KEY=...
├── roadpulse.db            # created on first run
├── static/
│   ├── css/style.css
│   ├── js/
│   │   ├── map.js          # Leaflet init, marker rendering, heatmap
│   │   ├── report.js       # geolocation + upload form
│   │   └── admin.js        # dashboard charts/table
│   └── uploads/             # saved incident photos
└── templates/
    ├── index.html           # citizen map + report UI
    └── admin.html            # admin dashboard
```

### 5.2 Core Flask Routes

```python
# app.py
from flask import Flask, request, jsonify, render_template, g
import os, uuid, sqlite3
from db import get_db, init_db
from gemini_service import classify_image, generate_report_summary
from duplicate import find_duplicate
from scoring import compute_confidence, VERIFIED_THRESHOLD
from routing_rules import DEPARTMENT_MAP

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/api/report", methods=["POST"])
def report_incident():
    image = request.files["image"]
    lat = float(request.form["lat"])
    lon = float(request.form["lon"])
    gps_accuracy = float(request.form.get("gps_accuracy", 50))
    user_note = request.form.get("note", "")
    device_id = request.form.get("device_id", "anonymous")

    image_bytes = image.read()
    result = classify_image(image_bytes, user_note)

    if not result["is_valid_road_issue"]:
        return jsonify({"status": "rejected",
                         "reason": result.get("rejection_reason", "Not a recognizable road issue")}), 200

    db = get_db()
    dup = find_duplicate(db, lat, lon, result["incident_type"])
    if dup:
        db.execute("UPDATE incidents SET confirmations = confirmations + 1 WHERE id = ?", (dup["id"],))
        db.commit()
        return jsonify({"status": "duplicate_merged", "incident_id": dup["id"],
                         "confirmations": dup["confirmations"] + 1}), 200

    filename = f"{uuid.uuid4().hex}.jpg"
    image_path = os.path.join("static", "uploads", filename)
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    confidence = compute_confidence(result["confidence"], 0, gps_accuracy, reporter_trust=50)
    status = "verified" if confidence >= VERIFIED_THRESHOLD else "pending_review"
    department = DEPARTMENT_MAP.get(result["incident_type"], "Municipal Corporation")

    summary = generate_report_summary(result, department, lat, lon, user_note)

    cur = db.execute(
        """INSERT INTO incidents
           (incident_type, severity, confidence_score, status, lat, lon,
            description_user, ai_reasoning, ai_summary, department, image_path)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (result["incident_type"], result["severity"], confidence, status, lat, lon,
         user_note, result["reasoning"], summary["complaint_text"], department, image_path)
    )
    db.commit()
    return jsonify({"status": status, "incident_id": cur.lastrowid,
                     "severity": result["severity"], "department": department,
                     "explanation": summary["citizen_explanation"]}), 201

@app.route("/api/incidents")
def list_incidents():
    db = get_db()
    rows = db.execute("SELECT * FROM incidents WHERE duplicate_of IS NULL ORDER BY created_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/stats")
def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) c FROM incidents").fetchone()["c"]
    by_status = db.execute("SELECT status, COUNT(*) c FROM incidents GROUP BY status").fetchall()
    by_type = db.execute("SELECT incident_type, COUNT(*) c FROM incidents GROUP BY incident_type").fetchall()
    return jsonify({"total": total,
                     "by_status": {r["status"]: r["c"] for r in by_status},
                     "by_type": {r["incident_type"]: r["c"] for r in by_type}})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)   # 0.0.0.0 so your phone can reach it over Wi-Fi
```

Note `host="0.0.0.0"` — that's what lets a phone on the same Wi-Fi hit `http://<your-laptop-LAN-ip>:5000` for a live, no-deploy demo.

---

## 6. Frontend Implementation (Leaflet + Vanilla JS)

### 6.1 Map + Report Form (`templates/index.html`, trimmed)

```html
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
  <div id="map"></div>

  <button id="report-btn">📍 Report Issue</button>

  <div id="report-modal" class="hidden">
    <form id="report-form">
      <input type="file" id="photo" accept="image/*" capture="environment" required>
      <textarea id="note" placeholder="Optional note"></textarea>
      <button type="submit">Submit Report</button>
    </form>
    <div id="report-result"></div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
  <script src="{{ url_for('static', filename='js/map.js') }}"></script>
  <script src="{{ url_for('static', filename='js/report.js') }}"></script>
</body>
</html>
```

### 6.2 `static/js/map.js` — markers + heatmap

```javascript
const map = L.map('map').setView([25.2048, 55.2708], 12); // default center; recenter on geolocation

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors',
  maxZoom: 19
}).addTo(map);

const severityColor = { low: '#2ecc71', medium: '#f1c40f', high: '#e67e22', critical: '#e74c3c' };
let markersLayer = L.layerGroup().addTo(map);
let heatLayer = null;

async function loadIncidents() {
  const res = await fetch('/api/incidents');
  const incidents = await res.json();

  markersLayer.clearLayers();
  const heatPoints = [];

  incidents.forEach(inc => {
    const marker = L.circleMarker([inc.lat, inc.lon], {
      radius: 8,
      color: severityColor[inc.severity] || '#999',
      fillOpacity: 0.85
    }).bindPopup(`
      <b>${inc.incident_type.replace('_',' ')}</b> — ${inc.severity}<br>
      Status: ${inc.status} | Confidence: ${(inc.confidence_score*100).toFixed(0)}%<br>
      Department: ${inc.department}<br>
      <img src="/${inc.image_path}" width="180"><br>
      <small>${inc.ai_summary || ''}</small>
    `);
    markersLayer.addLayer(marker);

    const weight = { low: 0.3, medium: 0.5, high: 0.75, critical: 1.0 }[inc.severity] || 0.5;
    heatPoints.push([inc.lat, inc.lon, weight]);
  });

  if (heatLayer) map.removeLayer(heatLayer);
  heatLayer = L.heatLayer(heatPoints, { radius: 25, blur: 20 }).addTo(map);
}

loadIncidents();
setInterval(loadIncidents, 15000); // simple polling refresh, good enough for a demo
```

### 6.3 `static/js/report.js` — geolocation + upload

```javascript
document.getElementById('report-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const resultBox = document.getElementById('report-result');
  resultBox.textContent = 'Getting location...';

  navigator.geolocation.getCurrentPosition(async (pos) => {
    const formData = new FormData();
    formData.append('image', document.getElementById('photo').files[0]);
    formData.append('note', document.getElementById('note').value);
    formData.append('lat', pos.coords.latitude);
    formData.append('lon', pos.coords.longitude);
    formData.append('gps_accuracy', pos.coords.accuracy);
    formData.append('device_id', localStorage.getItem('device_id') || 'anon-' + Date.now());

    resultBox.textContent = 'Analyzing photo with AI...';
    const res = await fetch('/api/report', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.status === 'rejected') {
      resultBox.textContent = `Not accepted: ${data.reason}`;
    } else if (data.status === 'duplicate_merged') {
      resultBox.textContent = `Matches an existing report — confirmation count increased to ${data.confirmations}.`;
    } else {
      resultBox.textContent = `Reported as ${data.severity} priority → routed to ${data.department}. ${data.explanation}`;
      loadIncidents();
    }
  }, (err) => { resultBox.textContent = 'Location permission is required to report an issue.'; });
});
```

---

## 7. Safer-Route Feature (OSRM)

Building a custom routing graph with modified edge weights (as the original spec's `Cost = Distance + Traffic + Severity + ...` formula implies) means running your own OSRM instance with a custom `.lua` profile and rebuilding the graph — not a one-day task. The realistic substitute:

1. Call OSRM's public demo server with `alternatives=true` to get 2-3 candidate routes.
2. For each candidate route's polyline, check how many `high`/`critical` incidents fall within ~30m of the path (reuse the haversine helper against a sampled set of points along the polyline).
3. Score `route_risk = Σ severity_weight` and return the lowest-risk alternative first, labeled "Recommended (avoids N reported hazards)."

```python
# routing_service.py
import requests

OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"

def get_safer_route(origin, destination, incidents, buffer_m=30):
    coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    resp = requests.get(f"{OSRM_BASE}/{coords}",
                         params={"alternatives": "true", "geometries": "geojson", "overview": "full"},
                         timeout=10)
    routes = resp.json()["routes"]

    severity_weight = {"low": 1, "medium": 2, "high": 4, "critical": 8}
    scored = []
    for route in routes:
        pts = route["geometry"]["coordinates"][::5]  # sample every 5th point, keep it cheap
        risk = 0
        for lon, lat in pts:
            for inc in incidents:
                if inc["severity"] in ("high", "critical") and haversine_m(lat, lon, inc["lat"], inc["lon"]) <= buffer_m:
                    risk += severity_weight[inc["severity"]]
        scored.append({"geometry": route["geometry"], "distance_m": route["distance"],
                        "duration_s": route["duration"], "risk_score": risk})

    scored.sort(key=lambda r: (r["risk_score"], r["duration_s"]))
    return scored  # scored[0] is the recommended "safe" route
```

**Rate-limit discipline:** the OSRM demo server's usage policy caps this at "reasonable, non-commercial" traffic — self-throttle to well under 1 request/second in your own code, and don't hammer it while testing (write a tiny local cache or replay saved responses during development, and only hit the live server for the actual demo run).

---

## 8. Geocoding Notes (Nominatim)

Only needed if you let users type an address instead of dropping a pin. If you use it:

```python
def geocode(address: str):
    resp = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": address, "format": "json", "limit": 1},
                         headers={"User-Agent": "RoadPulseHackathon/1.0 (contact@example.com)"},
                         timeout=10)
    results = resp.json()
    return (float(results[0]["lat"]), float(results[0]["lon"])) if results else None
```

Nominatim's usage policy caps public requests at **1/sec** and requires a real `User-Agent`. For the demo, `navigator.geolocation` (device GPS) is the primary path — reserve Nominatim for the rare manual-address fallback so you never come close to the limit.

---

## 9. REST API Reference

| Method | Path | Body / Params | Returns |
|---|---|---|---|
| GET | `/` | — | Citizen map UI |
| GET | `/admin` | — | Admin dashboard UI |
| POST | `/api/report` | `image`, `lat`, `lon`, `gps_accuracy`, `note`, `device_id` (multipart) | `{status, incident_id, severity, department, explanation}` |
| GET | `/api/incidents` | — | JSON array of active (non-duplicate) incidents |
| GET | `/api/incidents/<id>` | — | Single incident detail |
| GET | `/api/stats` | — | `{total, by_status, by_type}` for dashboard |
| POST | `/api/confirm/<id>` | `vote` (`confirm`/`reject`) | Updates `confirmations`, adjusts confidence |
| POST | `/api/route` | `{origin:[lat,lon], destination:[lat,lon]}` | Ranked list of routes with `risk_score` |
| POST | `/api/resolve/<id>` | admin auth | Marks incident resolved, timestamps it |

---

## 10. One-Day MVP Prioritization

| Tier | Features |
|---|---|
| **Must Have** (build first, demo depends on these) | Photo upload + GPS capture · Gemini classification (type/severity/confidence/reasoning) · SQLite storage · Live Leaflet map with colored markers · Department routing table · LLM-generated complaint summary |
| **Should Have** (build if Must Have finishes early) | Duplicate detection + merge · Confidence-score formula + verified/pending status · Heatmap layer · Admin dashboard with stats · Emergency `tel:` links |
| **Nice to Have** | Safer-route OSRM feature · Citizen trust score · Confirmation voting (nearby users confirm/reject) · Simulated push-style toast notifications |
| **Stretch / Demo-Only Simulation** | "Prediction" risk layer seeded from synthetic historical data · Instagram-style share card generation · Weekly/monthly AI-generated summary text |
| **Explicitly Out of Scope for Day One** | Real CLIP/DBSCAN embeddings · Trained XGBoost/LightGBM models · Real SHAP/Grad-CAM · Custom OSRM graph with weighted edges · Real Instagram API posting · Multi-tenant auth/roles · Knowledge graph DB |

---

## 11. Hour-by-Hour Build Plan (≈12-hour day)

| Hours | Focus |
|---|---|
| 0–1 | Repo scaffold, `requirements.txt`, `.env`, Gemini API key test call (single curl/script), SQLite schema created |
| 1–3 | `gemini_service.py` (classify + generate), test against 5-10 real pothole/flood photos pulled from the web, tune the prompt until JSON is reliable |
| 3–4 | `/api/report` end-to-end (upload → classify → store), duplicate detection, confidence formula, department table |
| 4–6 | Frontend: map, marker rendering, report modal, geolocation, upload flow wired to the live backend |
| 6–7 | Heatmap layer, `/api/stats`, admin dashboard page |
| 7–8 | Safer-route OSRM feature |
| 8–9 | Trust score counter, confirmation voting, emergency `tel:` links, UI polish/CSS pass |
| 9–10 | Seed 30-50 synthetic historical incidents (script, not manual) so the map/heatmap/dashboard don't look empty; write the risk-layer heuristic on top of that seed data |
| 10–11 | Full run-through on the actual demo phone + laptop over venue Wi-Fi, fix whatever breaks (it will be the Wi-Fi/GPS permissions, budget real time for this) |
| 11–12 | Freeze scope, rehearse the 5-minute demo script (§13), prep answers for the "why not real ML here" questions using §0's table |

---

## 12. Using Claude to Generate This Codebase

A sensible order of Claude Code prompts, one file/module at a time rather than "build the whole app" in one shot (smaller asks are easier to review and fix mid-build):

1. *"Scaffold the Flask project structure from §6.1, with an empty `schema.sql` matching §3 and a working `init_db()`."*
2. *"Implement `gemini_service.py` exactly as specified in §4.1 and §4.5, using the Gemini REST API with `response_schema`."*
3. *"Implement `duplicate.py` and `scoring.py` from §4.2 and §4.3."*
4. *"Implement `app.py` routes from §5.2, wiring together the modules above."*
5. *"Build `templates/index.html`, `static/js/map.js`, `static/js/report.js` from §6."*
6. *"Build the admin dashboard (`templates/admin.html`, `static/js/admin.js`) reading from `/api/stats`."*
7. *"Implement `routing_service.py` and an `/api/route` endpoint from §7."*
8. *"Write a `seed_data.py` script that inserts ~40 synthetic historical incidents across a chosen city area with varied timestamps, types, and severities, for the demo."*
9. *"Do a final pass: error handling around the Gemini call (timeouts, malformed JSON), and a loading spinner in the UI while classification is running."*

Keep each prompt scoped to one module and paste the relevant section of this report in as the spec — that keeps Claude's output consistent with the architecture instead of inventing a different one each time.

---

## 13. Five-Minute Demo Script

| Time | Action | What judges see |
|---|---|---|
| 0:00–0:30 | Open the live map on your phone, pre-seeded with historical incidents + heatmap | Instant "this looks real" impression, no empty-state awkwardness |
| 0:30–1:30 | Photograph an actual pothole/puddle near the venue (or a prepared photo), submit through the report form | GPS auto-capture, upload, live "Analyzing with AI..." state |
| 1:30–2:15 | Result returns: type, severity, department routed to, and the one-sentence AI explanation | This is your XAI moment — read the explanation out loud |
| 2:15–2:45 | Second teammate submits a photo of the *same* spot | Live duplicate-merge: confirmation count increases instead of a new pin appearing |
| 2:45–3:30 | Switch to the map: point out the new marker, the heatmap shift, click the popup showing the AI-generated complaint text | Ties the whole pipeline together visually |
| 3:30–4:15 | Request a route through the area on the map; show the "recommended" route avoiding the just-reported hazard vs. the raw shortest path | Demonstrates the safer-routing payoff |
| 4:15–4:45 | Open the admin dashboard: totals, by-type breakdown, ward-ish grouping | Shows the government-facing side exists, not just the citizen app |
| 4:45–5:00 | Closing line: name the 3 substitutions you made (§0 table) and the 1-line production roadmap (§14) | Preempts "why isn't this using X model" questions before they're asked |

---

## 14. Environment Setup

```bash
# requirements.txt
flask==3.0.3
requests==2.32.3
python-dotenv==1.0.1
```

```bash
# .env
GEMINI_API_KEY=your_key_from_aistudio.google.com

# setup
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
# then, on the demo phone, open http://<laptop-LAN-IP>:5000  (same Wi-Fi network)
```

Get a free Gemini API key at **https://aistudio.google.com** — no credit card required for the Flash/Flash-Lite tier as of mid-2026, but **confirm the current free-tier terms on the day**, since Google adjusts these periodically (Pro-tier models went paid-only earlier in 2026; Flash/Flash-Lite have stayed free-tier-eligible).

---

## 15. Known Limitations (have these answers ready)

- **No custom-trained CV model** — by design; a hosted multimodal LLM replaces it (§0). Tradeoff: you're dependent on Gemini's uptime/latency during the demo; mitigate by pre-testing your exact demo photos beforehand and having a cached fallback response if Wi-Fi drops.
- **Duplicate detection is geo+type+time, not embeddings** — catches the common case, will occasionally over- or under-merge; stated as a v2 upgrade path (add text-embedding similarity).
- **Routing "safety" is a post-hoc risk score over OSRM alternatives, not a custom-weighted graph** — real production version needs a self-hosted OSRM instance with a custom profile so edge weights can actually change (§0 table); the demo server also isn't licensed for production traffic.
- **"Prediction" layer is a heuristic over seeded synthetic data, not a trained forecasting model** — because there's no real historical time series on day one; production version trains LightGBM/an LSTM once real incident history accumulates.
- **SQLite, no PostGIS, no auth system, no rate limiting on your own API** — all correct simplifications for a single-day, single-demo-instance build; explicitly the first three things to add before any real deployment.

---

## 16. Post-Hackathon Production Roadmap (one line each, for the closing slide)

1. **Data layer:** SQLite → PostgreSQL + PostGIS; real user auth; move images to cloud object storage.
2. **ML layer:** once real incident volume accumulates, train a lightweight fine-tuned or distilled vision classifier to cut per-report Gemini cost/latency at scale, keep an LLM in the loop only for summarization and edge cases.
3. **Routing layer:** self-host OSRM with a custom cost profile so hazard/flood/severity actually reweights the graph, instead of re-ranking demo-server alternatives.
4. **Trust/anti-abuse:** move the trust-score formula from a simple counter to a proper reputation model once there's abuse data to learn from.
5. **Ops:** add rate limiting, request auth, and monitoring/alerting before any public traffic — none of that exists in the one-day build on purpose.
