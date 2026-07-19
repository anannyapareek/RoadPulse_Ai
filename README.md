# RoadPulse AI

A one-day hackathon implementation of a smart city road incident reporting system powered by Gemini AI classification and Leaflet maps.

## Project Overview

RoadPulse AI enables mobile users to report road hazards (potholes, flooding, debris, accidents, etc.) with a photo and GPS location. The Gemini API automatically classifies incidents and assigns them to the appropriate municipal department. The system detects duplicate reports, computes confidence scores based on image quality and GPS accuracy, and provides real-time dashboards for city administrators.

**Architecture:**
- **Backend:** Flask + SQLite
- **AI Classification:** Google Gemini 1.5 Flash API (REST)
- **Maps:** Leaflet + OpenStreetMap
- **Frontend:** Plain HTML/CSS/JS (phase 2)

---

## Setup Instructions

### 1. Clone or Extract Project

```bash
cd roadpulse_ai
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example file and fill in your API key:

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL=gemini-1.5-flash
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
```

**Get a Gemini API Key:**
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Paste it into `.env`

### 5. Initialize Database

```bash
python app.py
```

Or use the Flask CLI:

```bash
export FLASK_APP=app.py
flask init-db
```

The database will be created at `instance/roadpulse.db` with tables for:
- `incidents` — reported road issues
- `devices` — reporting devices
- `verified_incidents` — admin-verified data
- `statistics` — cached metrics

### 6. Run the Server

```bash
python app.py
```

The server will start on `http://localhost:5000`.

---

## API Endpoints

### `POST /api/report`

Submit a new road incident report with image.

**Request:** Multipart form data

```bash
curl -X POST http://localhost:5000/api/report \
  -F "image=@photo.jpg" \
  -F "lat=40.7128" \
  -F "lon=-74.0060" \
  -F "gps_accuracy=15.0" \
  -F "note=Large pothole on Main St" \
  -F "device_id=my-device-001"
```

**Response:**

```json
{
  "success": true,
  "incident_id": 1,
  "classification": {
    "incident_type": "pothole",
    "severity_level": "high",
    "confidence_score": 0.92,
    "reason": "Visible road surface depression with visible edges"
  },
  "confidence": 0.87,
  "is_duplicate": false,
  "device_id": "my-device-001"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | File | Yes | Image file (JPG, PNG, GIF, WebP) |
| `lat` | Float | Yes | Latitude in decimal degrees |
| `lon` | Float | Yes | Longitude in decimal degrees |
| `gps_accuracy` | Float | No | GPS accuracy in meters (default: 25.0) |
| `note` | String | No | User note (max 500 chars) |
| `device_id` | String | No | Device identifier; auto-generated if omitted |

### `GET /api/incidents`

Fetch incident list with optional filtering.

**Request:**

```bash
curl 'http://localhost:5000/api/incidents?type=pothole&severity=high&limit=20'
```

**Response:**

```json
{
  "success": true,
  "incidents": [
    {
      "id": 1,
      "device_id": "abc123",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "incident_type": "pothole",
      "severity_level": "high",
      "confidence_score": 0.87,
      "notes": "Large pothole",
      "created_at": "2024-01-15 14:32:00",
      "routing_rule": {
        "department": "Public Works",
        "priority": "high",
        "response_time_hours": 24
      },
      "severity_color": "#F44336"
    }
  ],
  "total": 42,
  "count": 20
}
```

**Parameters:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | Int | 100 | Max results per request |
| `offset` | Int | 0 | Pagination offset |
| `type` | String | - | Filter by incident type |
| `severity` | String | - | Filter by severity level |
| `include_duplicates` | Bool | false | Include flagged duplicates |

### `GET /api/stats`

Fetch aggregated statistics.

**Request:**

```bash
curl 'http://localhost:5000/api/stats'
```

**Response:**

```json
{
  "success": true,
  "stats": {
    "total_incidents": 42,
    "total_devices": 18,
    "incidents_by_type": {
      "pothole": 15,
      "flooding": 8,
      "debris": 12,
      "other": 7
    },
    "incidents_by_severity": {
      "low": 10,
      "medium": 18,
      "high": 12,
      "critical": 2
    },
    "average_confidence": 0.756,
    "duplicate_count": 3
  }
}
```

### `GET /`

Root endpoint serving a placeholder homepage.

### `GET /admin`

Admin dashboard with incident table and aggregated statistics (HTML).

---

## Project Structure

```
roadpulse_ai/
├── app.py                          # Main Flask application with routes
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── README.md                       # This file
│
├── app/
│   ├── __init__.py                 # Flask app factory
│   ├── db.py                       # Database init and query helpers
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── gemini_service.py       # Gemini API integration
│   │
│   └── utils/
│       ├── __init__.py
│       ├── duplicate.py            # Haversine distance & duplicate detection
│       ├── scoring.py              # Confidence computation formula
│       ├── routing_rules.py        # Department assignment rules
│       └── utils.py                # General helpers (device ID, file upload)
│
├── migrations/
│   └── schema.sql                  # SQLite database schema
│
├── instance/
│   └── roadpulse.db                # Database file (auto-created)
│
└── uploads/
    └── (incident images)           # Uploaded photo files
```

---

## Database Schema

### `incidents`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | Primary key |
| `device_id` | TEXT | Reporting device ID |
| `latitude` | REAL | Decimal degrees |
| `longitude` | REAL | Decimal degrees |
| `gps_accuracy` | REAL | Accuracy in meters |
| `incident_type` | TEXT | pothole, crack, flooding, debris, accident, congestion, other |
| `severity_level` | TEXT | low, medium, high, critical |
| `confidence_score` | REAL | 0.0–1.0 |
| `notes` | TEXT | User note |
| `image_filename` | TEXT | Filename in uploads/ |
| `raw_gemini_response` | TEXT | Full Gemini API response |
| `created_at` | TIMESTAMP | ISO 8601 |
| `updated_at` | TIMESTAMP | ISO 8601 |
| `is_duplicate` | INTEGER | 0=original, 1=duplicate |
| `duplicate_of_id` | INTEGER | FK to original incident |

### `devices`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | Primary key |
| `device_id` | TEXT | Unique device identifier |
| `device_name` | TEXT | User-friendly name |
| `last_seen` | TIMESTAMP | Last activity |
| `total_reports` | INTEGER | Incident count |
| `is_active` | INTEGER | 1=active, 0=inactive |
| `created_at` | TIMESTAMP | Registration time |

### `verified_incidents`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | Primary key |
| `incident_id` | INTEGER | FK to incidents |
| `verified_type` | TEXT | Admin-verified type |
| `verified_severity` | TEXT | Admin-verified severity |
| `verified_by` | TEXT | Admin username |
| `verification_notes` | TEXT | Admin notes |
| `verified_at` | TIMESTAMP | Verification time |

---

## Gemini Service Details

### `classify_image(image_path, note="")`

Sends an image to Google's Gemini API and returns structured JSON classification.

**Input:**
- `image_path`: Path to image file (JPG, PNG, GIF, WebP)
- `note`: Optional user note

**Output:**
```json
{
  "incident_type": "pothole|crack|flooding|debris|accident|congestion|other",
  "severity_level": "low|medium|high|critical",
  "confidence_score": 0.0–1.0,
  "reason": "explanation"
}
```

**API Call:**
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent`
- Method: `POST`
- Headers: `Content-Type: application/json`
- Parameter: `?key=GEMINI_API_KEY`
- Response format: `application/json` (via `generationConfig.responseMimeType`)

### `generate_report_summary(...)`

Generates a human-readable 2–3 sentence summary for a report.

---

## Confidence Scoring Formula

```python
base_score = gemini_confidence  # 0.0–1.0 from Gemini
accuracy_factor = max(0.5, min(1.0, 100.0 / gps_accuracy))
duplicate_factor = 0.7 if is_duplicate else 1.0
final_confidence = base_score * accuracy_factor * duplicate_factor
```

**Example:**
- Gemini: 0.92 (high confidence)
- GPS accuracy: 15m → factor = 1.0 (excellent)
- Not a duplicate → factor = 1.0
- **Final: 0.92**

---

## Duplicate Detection

Uses **haversine distance** formula to detect reports within **50 meters** of the same incident type within a **24-hour** window.

```python
distance_km = haversine(lat1, lon1, lat2, lon2)
is_duplicate = (distance_km <= 0.05) and (same_type) and (within_24h)
```

If a duplicate is detected:
- `is_duplicate` flag is set to `1`
- `duplicate_of_id` references the original incident ID
- Confidence score is reduced by factor of 0.7

---

## Routing Rules

Incidents are automatically routed to departments based on type:

| Type | Department | Priority | Response Time |
|------|------------|----------|----------------|
| pothole | Public Works | high | 24h |
| crack | Public Works | medium | 48h |
| flooding | Drainage/Stormwater | **critical** | 4h |
| debris | Public Works | medium | 2h |
| accident | Emergency Services | **critical** | ASAP |
| congestion | Traffic Management | low | 1h |
| other | General Services | low | 48h |

---

## Testing

### 1. Create Test Image

```bash
# Use any JPEG or PNG file, or create a dummy one:
python -c "
from PIL import Image
img = Image.new('RGB', (640, 480), color='brown')
img.save('test_pothole.jpg')
"
```

### 2. Submit Report

```bash
curl -X POST http://localhost:5000/api/report \
  -F "image=@test_pothole.jpg" \
  -F "lat=40.7580" \
  -F "lon=-73.9855" \
  -F "gps_accuracy=12" \
  -F "note=Pothole on 5th Avenue" \
  -F "device_id=test-device-001"
```

### 3. View Results

- **API:** `curl http://localhost:5000/api/incidents`
- **Dashboard:** Open `http://localhost:5000/admin` in a browser

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | (required) | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Model to use |
| `FLASK_ENV` | `development` | Flask environment |
| `FLASK_DEBUG` | `True` | Enable debug mode |
| `SECRET_KEY` | `dev-secret-key...` | Session secret (change in production!) |
| `DATABASE_URL` | `sqlite:///instance/roadpulse.db` | Database connection string |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `5000` | Server port |

---

## Known Limitations & Roadmap

### Phase 1 (Complete)
- ✅ Gemini image classification (REST API)
- ✅ Database schema and queries
- ✅ /api/report, /api/incidents, /api/stats endpoints
- ✅ Duplicate detection (haversine)
- ✅ Confidence scoring
- ✅ Department routing rules

### Phase 2 (Frontend)
- ⏳ Leaflet map with markers
- ⏳ Mobile-friendly image upload UI
- ⏳ Real-time incident feed
- ⏳ Admin verification interface
- ⏳ Map clustering and heatmaps

### Phase 3 (Production)
- ⏳ Authentication & API keys
- ⏳ Rate limiting
- ⏳ Image optimization and storage (S3/GCS)
- ⏳ WebSocket live updates
- ⏳ Email/SMS notifications

---

## License

MIT License — See LICENSE file.

---

## Support

For issues or questions:
1. Check the API responses (they include error messages)
2. Review the Flask logs: `FLASK_DEBUG=True` shows detailed errors
3. Verify your Gemini API key is correct and has quota

---

## Quick Reference

**Start server:**
```bash
python app.py
```

**Initialize DB:**
```bash
flask init-db
```

**Test endpoint:**
```bash
curl http://localhost:5000/api/stats
```

**View admin dashboard:**
Open `http://localhost:5000/admin`

---

**RoadPulse AI — Built in one day.** 🚗🗺️
