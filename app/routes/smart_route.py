"""
app/routes/smart_route.py

Smart Route Recommendation.
User types a location (free text); Gemini resolves it to lat/lon coordinates,
then the TomTom routing API handles actual polyline/travel-time computation.
Optionally biases suggestions by warning about high-confidence incidents near
the destination (no full graph re-weighting -- that is explicitly out of scope).

Register with:
    from app.routes.smart_route import smart_route_bp
    app.register_blueprint(smart_route_bp)
"""

import os
import json
import requests
from flask import Blueprint, request, jsonify

from app.db import query_db

smart_route_bp = Blueprint("smart_route", __name__)

GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models'


def geocode_with_gemini(location_text: str, city_hint: str = "Abu Dhabi") -> dict:
    """
    Asks Gemini to resolve a free-text location into approximate coordinates.
    Returns {"lat": float, "lon": float, "resolved_name": str} or raises ValueError.
    """
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")

    url = f"{GEMINI_API_URL}/{model_name}:generateContent"

    prompt = (
        f"Resolve this location to approximate latitude/longitude coordinates: "
        f'"{location_text}". Assume it is in or near {city_hint} unless the text '
        f"clearly states another city. Respond ONLY with a valid JSON object matching exactly this format: "
        f'{{"lat": 28.6139, "lon": 77.2090, "resolved_name": "New Delhi"}}. '
        f"Do not include markdown blocks or any other text."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    headers = {'Content-Type': 'application/json'}

    response = requests.post(url, headers=headers, json=payload, params={'key': api_key}, timeout=15)
    response.raise_for_status()
    
    response_json = response.json()
    if 'candidates' not in response_json or not response_json['candidates']:
        raise ValueError("No candidates in Gemini response")
        
    try:
        raw = response_json['candidates'][0]['content']['parts'][0]['text'].strip()
        import re
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        data = json.loads(raw.strip())
    except Exception as e:
        raise ValueError(f"Failed to parse Gemini JSON: {e}")

    if "lat" not in data or "lon" not in data:
        raise ValueError("Gemini geocode response missing lat/lon")
    
    return data


def _nearby_incident_penalty(lat: float, lon: float, radius_km: float = 0.5) -> float:
    """
    Returns a 0-1 penalty factor based on nearby high-confidence active incidents
    near the destination. Uses the same rough Haversine approximation as duplicate.py.
    """
    rows = query_db(
        "SELECT latitude, longitude, confidence_score FROM incidents "
        "WHERE is_duplicate = 0 AND created_at > datetime('now', '-6 hours')"
    )
    penalty = 0.0
    for row in rows:
        inc_lat = row["latitude"]
        inc_lon = row["longitude"]
        confidence = row["confidence_score"]
        # Cheap flat-earth approximation; fine at sub-km radius
        dist_km = ((inc_lat - lat) ** 2 + (inc_lon - lon) ** 2) ** 0.5 * 111
        if dist_km <= radius_km:
            penalty = max(penalty, confidence)
    return penalty


@smart_route_bp.route("/smart-route", methods=["POST"])
def smart_route():
    """
    Body: {"start_text": "...", "end_text": "...", "city_hint": "Abu Dhabi" (optional)}
    Resolves both locations via Gemini, then calls OpenStreetMap (OSRM) to get the route polyline.
    """
    data = request.json or {}
    start_text = data.get("start_text")
    end_text = data.get("end_text")
    city_hint = data.get("city_hint", "Abu Dhabi")

    if not start_text or not end_text:
        return jsonify({"error": "start_text and end_text are required"}), 400

    try:
        start = geocode_with_gemini(start_text, city_hint)
        end = geocode_with_gemini(end_text, city_hint)
    except (ValueError, json.JSONDecodeError) as e:
        return jsonify({"error": f"Could not resolve location: {e}"}), 422

    # OSRM expects coordinates in lon,lat format
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start['lon']},{start['lat']};{end['lon']},{end['lat']}?geometries=geojson"
    )

    try:
        headers = {'User-Agent': 'RoadPulse-MVP-Agent/1.0'}
        res = requests.get(url, headers=headers, timeout=10).json()
        
        if res.get('code') != 'Ok':
            return jsonify({"error": "OSRM routing failed: " + res.get('message', 'Unknown error')}), 500

        route = res['routes'][0]
        # OSRM returns coordinates as [lon, lat], Leaflet wants [lat, lon]
        polyline = [[p[1], p[0]] for p in route['geometry']['coordinates']]
        
        incident_risk = _nearby_incident_penalty(end["lat"], end["lon"])

        return jsonify({
            "resolved_start": start,
            "resolved_end": end,
            "polyline": polyline,
            "travel_time_minutes": route["duration"] // 60,
            "distance_km": round(route["distance"] / 1000, 2),
            "destination_incident_risk": round(incident_risk, 2),
            "risk_warning": incident_risk > 0.6,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
