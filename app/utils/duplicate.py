"""Duplicate incident detection using geospatial hashing."""

import math
from typing import List, Dict, Optional, Tuple


EARTH_RADIUS_KM = 6371.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points on Earth.
    
    Args:
        lat1 (float): Latitude of first point in degrees.
        lon1 (float): Longitude of first point in degrees.
        lat2 (float): Latitude of second point in degrees.
        lon2 (float): Longitude of second point in degrees.
    
    Returns:
        float: Distance in kilometers.
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return EARTH_RADIUS_KM * c


def find_duplicate(
    latitude: float,
    longitude: float,
    incident_type: str,
    existing_incidents: List[Dict]
) -> Optional[Tuple[int, float, float]]:
    """Find if this incident matches an existing one within spatial/temporal bounds.
    
    Criteria:
    - Distance within 50 meters (0.05 km)
    - Same incident type
    - Reported within last 24 hours (checked externally; we only check location + type here)
    
    Args:
        latitude (float): Latitude of new incident.
        longitude (float): Longitude of new incident.
        incident_type (str): Type of incident.
        existing_incidents (List[Dict]): List of existing incident records.
                                         Expected keys: 'id', 'latitude', 'longitude', 'incident_type'
    
    Returns:
        Tuple[int, float, float]: (incident_id, distance_km, distance_m) of matching incident,
                                  or None if no match found.
    """
    threshold_km = 0.05  # 50 meters
    
    for incident in existing_incidents:
        if incident.get('incident_type') != incident_type:
            continue
        
        distance_km = haversine(
            latitude,
            longitude,
            incident['latitude'],
            incident['longitude']
        )
        
        if distance_km <= threshold_km:
            distance_m = distance_km * 1000
            return (incident['id'], distance_km, distance_m)
    
    return None
