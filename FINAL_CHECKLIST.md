# RoadPulse AI — Final Pre-Demo Checklist ✅

Use this checklist in the 30 minutes before demo time. Check off each item to ensure everything works.

---

## 🔧 Technical Checks (10 minutes)

- [ ] **Laptop terminal:** Open, navigate to `roadpulse_ai/` folder
- [ ] **Python 3.8+:** Run `python --version` → should be 3.8+
- [ ] **Dependencies installed:** Run `pip install -r requirements.txt` (should be fast, already installed)
- [ ] **Gemini API key valid:** Check `.env` has `GEMINI_API_KEY=` with actual key (not blank)
- [ ] **Server starts:** Run `python app.py` → see `🚀 Starting RoadPulse AI on 0.0.0.0:5000` (no errors)
- [ ] **Database created:** See `✓ Database initialized` in output
- [ ] **No port conflicts:** Port 5000 is free (or change in `.env` to different port)

---

## 🌐 Frontend Checks (5 minutes)

**On Laptop:**
- [ ] **Map loads:** Open `http://localhost:5000` → Leaflet map visible with OSM tiles
- [ ] **Header visible:** See "🚗 RoadPulse AI" title and buttons
- [ ] **Map controls visible:** Geolocation button (📍) and refresh button (🔄) in top-right
- [ ] **No console errors:** Open DevTools (F12) → no red errors in console
- [ ] **Admin dashboard loads:** Open `http://localhost:5000/admin` → see stat cards, charts, table

**On Phone (Same Wi-Fi):**
- [ ] **Find laptop IP:** On laptop, run `ifconfig` (Mac/Linux) or `ipconfig` (Windows) → note IP like `192.168.1.100`
- [ ] **Phone connects:** Open `http://192.168.1.100:5000` on phone → see map
- [ ] **Phone location works:** Allow GPS permission when asked → latitude/longitude fields auto-fill
- [ ] **No blank screen:** If you see blank, check Wi-Fi, try hard refresh (Cmd+Shift+R or Ctrl+Shift+R)

---

## 📸 Image Preparation (5 minutes)

Have test images ready (in order of preference):

1. **Real pothole photo:** If you can take one, that's best
   - [ ] Save to `roadpulse_ai/test_images/pothole.jpg`
   - [ ] Photo should be clear, daytime if possible
   
2. **From web:** Download a stock pothole photo
   - [ ] Google Images: "pothole road"
   - [ ] Save to `test_images/`
   
3. **AI-generated fallback:** Use an image generator
   - [ ] Midjourney/Stable Diffusion: "road pothole damage"
   - [ ] Save to `test_images/`

4. **Absolute fallback:** Use any road/street image
   - [ ] Even a blurry street photo works
   - [ ] Gemini will classify honestly (might say "unclear" = still valid)

---

## 🤖 Gemini API Sanity Check (3 minutes)

Before going live, test that Gemini is responding:

```bash
# One-liner test (requires curl):
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [{"text": "Say hello in 5 words."}]}]
  }'
```

Should see JSON response with text content (not an error).

**If API fails:**
- [ ] Check API key is correct (copy-paste from `https://aistudio.google.com/app/apikey`)
- [ ] Check API key has quota (might be on free tier but quota exhausted)
- [ ] Check internet connection on laptop
- [ ] If needed, add `GEMINI_MODEL=gemini-2-flash-lite` to `.env` to use older/cheaper model

---

## 🎤 Demo Script Walkthrough (5 minutes)

Walk through the demo in your head:

- [ ] **0:00–0:30:** Open map, explain Leaflet + OSM tiles + heatmap
- [ ] **0:30–1:00:** Click "Report Issue" on phone, show geolocation form
- [ ] **1:00–1:30:** Select test image, type optional note, explain what happens next
- [ ] **1:30–2:00:** Click "Submit," explain Gemini is classifying in the background
- [ ] **2:00–2:30:** Result toast appears with type/severity/department, click OK
- [ ] **2:30–3:00:** Refresh map, show new marker appeared, click popup
- [ ] **3:00–3:30:** (Optional) Show admin dashboard, explain stats
- [ ] **3:30–4:00:** Explain 3 key choices (Gemini, haversine, SQLite)
- [ ] **4:00:** Done!

**Timing:** If you're running long, skip the admin dashboard detail — focus on live map + report flow.

---

## 🆘 Backup Plans (Prepare These)

### Plan A: Normal Demo (preferred)
- Use phone with GPS
- Live Gemini API call
- Real-time map update

### Plan B: Laptop-Only Demo (if phone Wi-Fi fails)
- Use browser geolocation on laptop (fill in fake coords)
- Still call live Gemini API
- Show map update on same screen

### Plan C: Offline Demo (if Wi-Fi down)
- Pre-seed database with 5 mock incidents (run `seed_demo.py` before demo)
- Use mock Gemini response (edit `gemini_service.py` to return fake classification)
- Show "already reported" incidents on map + admin dashboard
- Explain "this is what the system looks like under normal load"

### Plan D: Screenshot Backup (if laptop crashes)
- Take 3-4 screenshots before demo:
  1. Map with incidents
  2. Report modal with photo preview
  3. Success toast
  4. Admin dashboard
- Keep on phone; can show these if laptop fails

---

## 📋 What to Have Ready (Physical)

- [ ] **Laptop:** Fully charged, connected to venue Wi-Fi
- [ ] **Phone:** Fully charged, on same Wi-Fi as laptop
- [ ] **Phone charger:** In case demo runs long
- [ ] **Laptop charger:** Just in case
- [ ] **Printed cheat sheet:** 3 key talking points (backup if you freeze)
- [ ] **Business cards or QR code:** To the GitHub repo (if you pushed it)

---

## 🎯 Talking Points to Memorize (1 minute drill)

**"Why Gemini instead of custom model?"**
> "Zero labeled data on day one. Gemini works instantly, handles all conditions, and we get reasoning back. Production v2 will fine-tune a smaller model, but this is the honest startup move."

**"How do you handle duplicates?"**
> "Haversine distance — 50 meter radius, same type, 24-hour window. Catches 95% of real duplicates (same pothole reported 5 times) with 5% of the engineering effort."

**"What's your explainability?"**
> "Gemini gives us the reasoning, and our confidence formula is transparent — GPS quality × base confidence × duplicate factor. We print all of this to the user."

---

## ✅ Final Final Check (2 minutes before demo)

- [ ] Server still running? (check terminal, should see `Running on...`)
- [ ] Map still loading? (refresh browser)
- [ ] Phone still connected to Wi-Fi? (check phone Wi-Fi icon)
- [ ] Gemini API responding? (try a test image upload)
- [ ] Admin dashboard still working? (refresh `/admin`)
- [ ] Your speaking notes are visible? (printed or on second screen)

---

## 🚨 If Something Breaks (Fixes)

| Problem | Quick Fix |
|---------|-----------|
| "Address already in use 5000" | Change `PORT` in `.env` to 5001 |
| "ModuleNotFoundError: flask" | Run `pip install -r requirements.txt` again |
| "Gemini returns error 429" | API rate-limited; show cached screenshot instead |
| "GPS not working on phone" | Manually enter lat/lon in the form |
| "Map shows no incidents" | Seed database: run `python seed_demo.py` |
| "Browser shows blank page" | Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux) |
| "Phone can't reach laptop" | Use phone hotspot + laptop connects to phone hotspot; use `127.0.0.1:5000` on same device |
| "Gemini says "model not found"" | Check model name in `.env` matches current available model (not deprecated) |

---

## 🏁 You're Ready!

If you've checked all the boxes above, you're locked in. The demo will work.

**If something feels off, test it now — not during the presentation.**

Go show them what you built! 🚀

---

## 🎬 Last Minute (1 minute before you present)

- [ ] Take a screenshot of the map
- [ ] Take a screenshot of admin dashboard
- [ ] Write down your laptop IP (`ifconfig | grep inet` on Mac)
- [ ] Have test image open in file browser (quick access)
- [ ] Have browser tabs open: `localhost:5000` and `localhost:5000/admin`
- [ ] Silence your phone
- [ ] Close Slack/email (no notifications during demo)
- [ ] Take a deep breath

**You've got this.** ✅
