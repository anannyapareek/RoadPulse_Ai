# RoadPulse AI — Quick Start (TL;DR)

## 30-Second Setup

```bash
# 1. Navigate to project
cd roadpulse_ai

# 2. Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
.\venv\Scripts\Activate.ps1  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp .env.example .env

# 5. Edit .env — add your Gemini API key
# Get key at: https://aistudio.google.com/app/apikey
nano .env  # or use your editor

# 6. Run server
python app.py

# 7. Open browser
# http://localhost:5000
```

---

## Login with Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| **Admin/Operator** | `admin` | `pulse2026` |
| **Citizen** | `citizen` | `user2026` |

---

## What to Test

### As Citizen:
1. ✅ Click map to set location
2. ✅ Upload an image (any JPG/PNG)
3. ✅ Add a note (e.g., "Pothole on Main St")
4. ✅ Click "Submit Urgent Report"
5. ✅ Watch Gemini AI classify it
6. ✅ See incident appear on map
7. ✅ Click marker to view XAI confidence breakdown

### As Operator:
1. ✅ View all incidents on dashboard
2. ✅ See live incident feed
3. ✅ Test "Avoidance Router" tab (set coordinates, click "Detour Path")
4. ✅ View statistics

---

## Troubleshooting in 10 Seconds

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Run: `source venv/bin/activate` |
| `GEMINI_API_KEY not configured` | Add key to `.env` file |
| Port 5000 in use | Run: `PORT=5001 python app.py` |
| Database locked | Press Ctrl+C, restart: `python app.py` |
| Gemini API error | Get new key at aistudio.google.com |

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `app.py` | Main Flask server |
| `templates/index.html` | Web interface (Jinja2) |
| `static/js/main.js` | Frontend logic |
| `static/js/api.js` | API fetch wrapper |
| `.env` | API keys & config (YOU CREATE) |
| `instance/roadpulse.db` | Local SQLite database |

---

## Full Guide?

👉 See **LOCAL_SETUP_GUIDE.md** for detailed instructions

---

**Server running? Open http://localhost:5000 🚀**
