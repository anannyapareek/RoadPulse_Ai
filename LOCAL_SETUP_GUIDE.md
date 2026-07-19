# RoadPulse AI — Local Development Setup Guide

## Prerequisites

- **Python 3.8+** installed
- **Git** (optional, for cloning)
- **A modern web browser** (Chrome, Firefox, Safari, Edge)
- **Google Gemini API key** (free tier available at https://aistudio.google.com/app/apikey)

---

## Step 1: Clone/Navigate to Project

```bash
# If you don't have the repo yet
git clone <your-repo-url>
cd roadpulse_ai

# Or if you already have it
cd /path/to/roadpulse_ai
```

---

## Step 2: Create & Activate Virtual Environment

### On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### On Windows (Command Prompt):
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

✅ You should see `(venv)` prefix in your terminal prompt after activation.

---

## Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- Flask (web framework)
- python-dotenv (environment variables)
- google-genai (Gemini API SDK)
- requests (HTTP client)
- Pillow (image handling)
- And other dependencies

⏱️ Should take 2-5 minutes depending on your internet speed.

---

## Step 4: Configure Environment Variables

### Create `.env` file in project root:

```bash
# macOS / Linux
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env

# Windows (Command Prompt)
copy .env.example .env
```

### Edit `.env` with your Gemini API key:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///instance/roadpulse.db
HOST=0.0.0.0
PORT=5000
```

**How to get a Gemini API key:**
1. Go to https://aistudio.google.com/app/apikey
2. Click **"Create API Key"**
3. Copy the key
4. Paste into `.env` file

---

## Step 5: Initialize Database

```bash
# Create database and schema
python app.py
```

**Output should show:**
```
✓ Database initialized
✓ Schema updates applied
[SYSTEM] Twilio Voice dispatch protocol online.
🚀 Starting RoadPulse AI on 0.0.0.0:5000
```

If you see errors, check:
- ✅ `.env` file exists and has valid `GEMINI_API_KEY`
- ✅ `requirements.txt` installed correctly
- ✅ Python version 3.8+

---

## Step 6: Run the Development Server

```bash
python app.py
```

**Expected output:**
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
 * Press CTRL+C to quit
```

✅ Server is now running!

---

## Step 7: Open in Browser

### Option A: Local Machine
Open your browser and navigate to:
```
http://localhost:5000
```

### Option B: Mobile Device (Same Wi-Fi)
1. Find your computer's local IP address:
   - **macOS/Linux**: `ifconfig | grep inet` (look for 192.168.x.x)
   - **Windows PowerShell**: `ipconfig` (look for IPv4 Address)

2. On your phone's browser, go to:
   ```
   http://192.168.X.XXX:5000
   ```
   (Replace X's with your actual IP)

---

## Step 8: Login & Test

### Demo Credentials (Pre-configured)

**Operator/Admin Dashboard:**
- Username: `admin`
- Password: `pulse2026`

**Citizen/Reporting Portal:**
- Username: `citizen`
- Password: `user2026`

### Quick Test Workflow

1. **Login** as `citizen` / `user2026`
2. **Click map** to populate coordinates
3. **Upload image** or use demo presets
4. **Enter observation** (e.g., "Large pothole on Main Street")
5. **Submit** — watch the Gemini AI classify it
6. **View on map** — new incident appears as a marker
7. **Inspect incident** — click marker to see XAI confidence breakdown
8. **Export share card** — generate Instagram-ready graphic

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'flask'"

**Solution:** Make sure virtual environment is activated
```bash
# Check if (venv) appears in terminal prompt
# If not, activate it:
source venv/bin/activate  # macOS/Linux
# or
.\venv\Scripts\Activate.ps1  # Windows
```

### Issue: "GEMINI_API_KEY not configured in environment"

**Solution:** Check `.env` file
```bash
# Make sure .env exists and has this line:
cat .env | grep GEMINI_API_KEY

# Should show:
# GEMINI_API_KEY=sk-xxxxxxx...

# If blank or missing, edit .env and add your key
```

### Issue: "Address already in use" (Port 5000)

**Solution A:** Kill the process using port 5000
```bash
# macOS/Linux
lsof -i :5000
kill -9 <PID>

# Windows PowerShell
Get-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess | Stop-Process

# Or just use a different port:
PORT=5001 python app.py
```

**Solution B:** Use a different port
```bash
# Edit .env:
PORT=5001

# Then restart:
python app.py
```

### Issue: "sqlite3.OperationalError: database is locked"

**Solution:** Database file is being used by another process
```bash
# Restart the server (Ctrl+C, then):
python app.py
```

### Issue: "Gemini API returned error"

**Possible causes:**
- ❌ API key is invalid/expired
- ❌ API key doesn't have Gemini enabled
- ❌ Rate limit exceeded (free tier: 60 requests/minute)
- ❌ No internet connection

**Solution:**
1. Generate a new API key at https://aistudio.google.com/app/apikey
2. Update `.env` with new key
3. Restart server

---

## File Structure Check

Verify these files exist before starting:

```
roadpulse_ai/
├── app.py                          ✅ Main Flask app
├── requirements.txt                ✅ Dependencies
├── .env                            ✅ Environment (YOU CREATE)
├── .env.example                    ✅ Template
├── templates/
│   └── index.html                  ✅ Flask template
├── static/
│   ├── css/
│   │   └── style.css               ✅ Stylesheet
│   └── js/
│       ├── api.js                  ✅ Fetch wrapper
│       └── main.js                 ✅ Core logic
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── services/
│   │   └── gemini_service.py
│   ├── routes/
│   │   ├── dashboard.py
│   │   ├── smart_route.py
│   │   └── community_validation.py
│   ├── utils/
│   └── integrations/
├── migrations/
│   ├── schema.sql
│   └── schema_updates.sql
├── instance/
│   └── roadpulse.db                ✅ Created on first run
└── uploads/                         ✅ Created on first run
```

---

## Development Tips

### Enable Auto-Reload on File Changes
Already enabled with `FLASK_DEBUG=True` in `.env`. Just save files and browser will refresh.

### View Server Logs
The terminal running `python app.py` shows real-time logs:
```
[SYSTEM] Twilio Voice dispatch protocol online.
[IDLE] Scanning live environment feeds for high-confidence anomalies.
```

### Clear Database & Start Fresh
```bash
# Delete the database file
rm instance/roadpulse.db

# Restart server (it will recreate the DB)
python app.py
```

### Test API Endpoints Directly

Using `curl`:
```bash
# Get all incidents
curl http://localhost:5000/api/incidents

# Get statistics
curl http://localhost:5000/api/stats

# Submit a report (with image)
curl -X POST http://localhost:5000/api/report \
  -F "image=@/path/to/image.jpg" \
  -F "lat=28.6139" \
  -F "lon=77.2090" \
  -F "gps_accuracy=15.0" \
  -F "note=Test pothole" \
  -F "device_id=test-device-001"
```

Using Python:
```python
import requests

# Fetch incidents
response = requests.get('http://localhost:5000/api/incidents')
print(response.json())
```

---

## Common Workflows

### Workflow 1: Test Citizen Reporting

1. Start server: `python app.py`
2. Open browser: `http://localhost:5000`
3. Login: `citizen` / `user2026`
4. Click on map to auto-populate coordinates
5. Upload an image (any JPG/PNG file)
6. Add note: "Test pothole - Main Street"
7. Click "Submit Urgent Report"
8. Watch Gemini classify it
9. Click map marker to inspect with XAI

### Workflow 2: Test Operator Dashboard

1. Start server: `python app.py`
2. Open browser: `http://localhost:5000`
3. Login: `admin` / `pulse2026`
4. See all incidents on map
5. Click "Overview Dashboard" tab
6. View live incident feed with confidence scores
7. Click incident to inspect full details

### Workflow 3: Test Safe Routing

1. Login as operator
2. Click "Avoidance Router" tab
3. Edit coordinates or use defaults
4. Click "Detour Path"
5. Watch route polyline appear on map
6. Green path avoids incident hotspots

---

## Stopping the Server

Press `Ctrl+C` in the terminal running `python app.py`:

```bash
Keyboard interrupt received, shutting down.
 * Serving Flask app 'app'
```

---

## Next Steps

Once server is running:

1. **Explore the UI** — try both operator and citizen roles
2. **Submit test incidents** — watch Gemini classify them in real-time
3. **Check database** — open `instance/roadpulse.db` with SQLite viewer
4. **Review logs** — check `app.py` console output for errors
5. **Read API docs** — open any endpoint in browser (e.g., `/api/stats`)
6. **Modify .env** — try changing ports, debug settings, etc.

---

## Performance Notes

- **First request slow?** — Gemini API warms up on first call (5-10 seconds)
- **Map stuttering?** — Try disabling heatmap layer (click "Pins View")
- **Database slow?** — SQLite fine for dev; upgrade to PostgreSQL for production
- **Out of memory?** — Reduce map zoom level or limit incidents returned

---

## Questions?

Check these files for more context:
- **README.md** — Full project overview
- **PROJECT_SUMMARY.md** — Architecture decisions
- **FRONTEND_REFACTOR_SUMMARY.md** — Frontend structure
- **app.py** — Main Flask application
- **static/js/main.js** — Frontend logic

---

**You're all set! 🚀 Happy developing!**
