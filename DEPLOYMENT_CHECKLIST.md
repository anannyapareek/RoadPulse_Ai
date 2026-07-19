# Deployment Verification Checklist

Use this checklist to verify everything is set up correctly before running the app.

## Pre-Flight Checklist

### Environment Setup
- [ ] Python 3.8+ installed: `python3 --version`
- [ ] Virtual environment created: `ls venv/` or `dir venv`
- [ ] Virtual environment activated: `(venv)` shows in terminal prompt
- [ ] Dependencies installed: `pip list | grep -i flask`

### Configuration
- [ ] `.env` file exists in project root: `ls .env` or `dir .env`
- [ ] `.env` contains `GEMINI_API_KEY=...` (not blank)
- [ ] `.env` contains `FLASK_DEBUG=True` for dev mode
- [ ] Gemini API key is valid (test at aistudio.google.com)

### File Structure
- [ ] `app.py` exists in root
- [ ] `templates/index.html` exists
- [ ] `static/js/main.js` exists
- [ ] `static/js/api.js` exists
- [ ] `static/css/style.css` exists
- [ ] `app/` directory with `__init__.py`, `db.py`, `services/`, `routes/`
- [ ] `migrations/` directory with `schema.sql`

### Database
- [ ] `instance/` directory will be created on first run
- [ ] `instance/roadpulse.db` will be auto-created
- [ ] `uploads/` directory will be created on first run

---

## Startup Verification

### Step 1: Start Server
```bash
python app.py
```

**Expected output:**
```
✓ Database initialized
✓ Schema updates applied
[SYSTEM] Twilio Voice dispatch protocol online.
[IDLE] Scanning live environment feeds...
🚀 Starting RoadPulse AI on 0.0.0.0:5000
```

**If you see errors:**
- ❌ `GEMINI_API_KEY not configured` → Add key to `.env`
- ❌ `ModuleNotFoundError` → Run `pip install -r requirements.txt`
- ❌ `Address already in use` → Change port in `.env` or kill process
- ❌ `database is locked` → Restart server

### Step 2: Open Browser
```
http://localhost:5000
```

**You should see:**
- ✅ Login screen with brand logo
- ✅ Dark theme (brandDarkCharcoal background)
- ✅ Demo credential buttons for "Citizen Portal" and "Operator Hub"
- ✅ No console errors (check browser DevTools → Console tab)

### Step 3: Test Login (Admin)

1. Click **"Operator Hub"** button or enter:
   - Username: `admin`
   - Password: `pulse2026`
2. Click **"Authenticate Access"**

**Expected:**
- ✅ Login screen hides
- ✅ App shell shows with map, sidebars, tabs
- ✅ Header shows "RoadPulse AI platform / Overview Console"
- ✅ Map displays (OpenStreetMap tiles visible)
- ✅ Right sidebar shows "Active GIS Incidents" section
- ✅ No errors in browser console

### Step 4: Test Map Functionality

1. **Click on the map** anywhere
2. **Coordinate fields auto-populate** in "Manual Dispatches" tab

**Expected:**
- ✅ Toast message: "Geographic coordinate captured from map selection"
- ✅ Latitude/longitude fields have values (e.g., 28.6139, 77.2090)

### Step 5: Test Citizen Login

1. Logout (click red logout button)
2. Click **"Citizen Portal"** button or enter:
   - Username: `citizen`
   - Password: `user2026`
3. Click **"Authenticate Access"**

**Expected:**
- ✅ Different UI: "Report Community Defect" form instead of multi-tabs
- ✅ Left sidebar shows different icons (file report, my reports, safe routing)
- ✅ Same map displays below form

### Step 6: Test Report Submission

1. Stay logged in as citizen
2. Click map to set coordinates
3. In "Evidence Snapshot Upload" section, select any image file
4. Add note: "Test pothole for verification"
5. Click **"Submit Urgent Report"**

**Expected:**
- ✅ Button shows spinner: "Processing Gemini Vision Pipeline"
- ✅ After 5-10 seconds, success toast appears
- ✅ Form clears
- ✅ New incident appears as marker on map
- ✅ Browser network tab shows `POST /api/report` call
- ✅ Response contains incident ID, classification, confidence score

### Step 7: Verify API Endpoints

Open new browser tab, go to:

**Stats endpoint:**
```
http://localhost:5000/api/stats
```

**Expected JSON response:**
```json
{
  "success": true,
  "stats": {
    "total_incidents": 1,
    "total_devices": 1,
    "incidents_by_type": {...},
    "average_confidence": 0.85,
    "duplicate_count": 0
  }
}
```

**Incidents endpoint:**
```
http://localhost:5000/api/incidents
```

**Expected JSON response:**
```json
{
  "success": true,
  "incidents": [
    {
      "id": 1,
      "incident_type": "pothole",
      "severity_level": "high",
      "confidence_score": 0.92,
      "latitude": 28.6139,
      "longitude": 77.2090,
      ...
    }
  ],
  "total": 1,
  "count": 1
}
```

---

## Browser Console Verification

Open **DevTools** (`F12` or `Cmd+Option+J` on Mac):

### Console Tab
- ✅ No red errors
- ✅ No "Uncaught" exceptions
- ✅ Check for: "Loading incidents from server..."

### Network Tab
When you submit a report, you should see:
- ✅ `POST /api/report` → Status 201
- ✅ `GET /api/incidents` → Status 200
- ✅ Request/response headers visible
- ✅ No 404 or 500 errors

### Application Tab
- ✅ Check `localStorage` for any stored values
- ✅ Check `Cookies` (should be empty for development)
- ✅ Check `IndexedDB` (should be empty)

---

## Database Verification

### Check SQLite Database File

```bash
# macOS/Linux
sqlite3 instance/roadpulse.db ".tables"

# Should show:
# devices  dispatch_logs  incidents  officer_assignments  ...
```

### View Incident Records

```bash
sqlite3 instance/roadpulse.db "SELECT id, incident_type, severity_level, confidence_score FROM incidents;"
```

**Expected output:**
```
1|pothole|high|0.92
2|flooding|critical|0.94
```

---

## Performance Verification

### First Request Timing
- ⚠️ First Gemini API call: **5-10 seconds** (normal, API warmup)
- ✅ Subsequent requests: **2-3 seconds** (cached)

### Map Performance
- ✅ Map loads in < 2 seconds
- ✅ Markers render instantly
- ✅ Heatmap layer renders in < 1 second
- ✅ Pan/zoom smooth (60 FPS target)

### Form Submission
- ✅ Form submission feedback immediate (loading spinner shows)
- ✅ Gemini classification: 5-10 seconds
- ✅ Map updates automatically after success

---

## Feature Verification

### All Features Should Work

| Feature | Check | Expected |
|---------|-------|----------|
| **Login** | Try both roles | No errors, correct UI |
| **Map** | Click to populate coords | Toast + form fields filled |
| **Report** | Submit with image | Success message + incident on map |
| **Inspect** | Click map marker | Detail drawer opens with XAI data |
| **Routing** | Enter coords, click "Detour" | Polyline appears on map |
| **Search** | Type in search box | Incident list filters |
| **Sidebar Toggle** | Click collapse buttons | Sidebars animate |
| **Tab Switch** | Click tab buttons | Content switches smoothly |
| **Canvas Export** | Click "Share Evidence" | Instagram card downloads |

---

## Common Issues & Fixes

### Issue: Blank Page After Login
**Check:**
- [ ] Browser console for errors (F12)
- [ ] Network tab for failed requests (check status codes)
- [ ] `.env` file has valid `GEMINI_API_KEY`
- [ ] `static/js/main.js` loaded (check Network tab)
- [ ] `static/js/api.js` loaded

**Fix:**
```bash
# Hard refresh
Ctrl+Shift+R  # Windows/Linux
Cmd+Shift+R   # Mac
```

### Issue: Map Not Displaying
**Check:**
- [ ] Browser console for Leaflet errors
- [ ] Network tab: `leaflet.css` and `leaflet.js` loaded
- [ ] `#map` element exists in HTML
- [ ] No CSS conflicts hiding the map

**Fix:**
```bash
# Clear browser cache
# Or hard refresh (see above)
```

### Issue: Gemini Errors on Report Submit
**Check:**
- [ ] API key is valid (copy from aistudio.google.com)
- [ ] API key has no spaces or hidden characters
- [ ] Rate limit not exceeded (free tier: 60 req/min)
- [ ] Internet connection is active

**Fix:**
```bash
# Get new API key from:
# https://aistudio.google.com/app/apikey
# Update .env
GEMINI_API_KEY=new_key_here
# Restart server
```

---

## Sign-Off

When all checkboxes above are ✅, you're ready to:

- [ ] **Deploy to production** (with proper security hardening)
- [ ] **Share with team members** (give them LOCAL_SETUP_GUIDE.md)
- [ ] **Integrate with CI/CD** (add GitHub Actions, Docker, etc.)
- [ ] **Scale to multiple users** (upgrade to PostgreSQL)

---

**Status: ✅ READY TO RUN LOCALLY**

Start the server with:
```bash
python app.py
```

Open browser to:
```
http://localhost:5000
```

**Happy testing! 🚀**
