"""Officer location tracking and nearest officer lookup service."""

import math
from app.db import query_db, execute_db


def update_officer_location(officer_id, lat, lon):
    """Update an officer's current location.
    
    Args:
        officer_id (int): Officer ID.
        lat (float): Latitude.
        lon (float): Longitude.
    
    Returns:
        dict: Updated location or error dict.
    """
    try:
        officer = query_db(
            'SELECT * FROM officers WHERE id = ?',
            (officer_id,),
            one=True
        )
        if not officer:
            return {'error': 'Officer not found'}
        
        execute_db(
            '''UPDATE officers 
               SET location_lat = ?, location_lon = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (lat, lon, officer_id)
        )
        
        return {
            'success': True,
            'officer_id': officer_id,
            'latitude': lat,
            'longitude': lon
        }
    except Exception as e:
        return {'error': str(e)}


def get_officer_location(officer_id):
    """Get an officer's current location.
    
    Args:
        officer_id (int): Officer ID.
    
    Returns:
        dict: Location with officer_id, latitude, longitude or error dict.
    """
    try:
        officer = query_db(
            'SELECT id, location_lat, location_lon FROM officers WHERE id = ?',
            (officer_id,),
            one=True
        )
        if not officer:
            return {'error': 'Officer not found'}
        
        if officer['location_lat'] is None or officer['location_lon'] is None:
            return {'error': 'Officer location not available'}
        
        return {
            'success': True,
            'officer_id': officer_id,
            'latitude': officer['location_lat'],
            'longitude': officer['location_lon']
        }
    except Exception as e:
        return {'error': str(e)}


def find_nearest_officers(incident_lat, incident_lon, count=3, radius_km=5):
    """Find the nearest available officers to an incident.
    
    Args:
        incident_lat (float): Incident latitude.
        incident_lon (float): Incident longitude.
        count (int): Number of officers to return (default 3).
        radius_km (float): Search radius in km (default 5).
    
    Returns:
        list: List of nearest officers sorted by distance, or error dict.
    """
    try:
        # Get all active officers with valid locations
        officers = query_db(
            '''SELECT id, name, badge_number, department, phone_number, 
                      location_lat, location_lon, rank, status
               FROM officers 
               WHERE status = 'active' 
               AND location_lat IS NOT NULL 
               AND location_lon IS NOT NULL
               ORDER BY location_lat DESC, location_lon DESC'''
        )
        
        if not officers:
            return []
        
        # Calculate distances and filter by radius
        nearby = []
        for officer in officers:
            dist = calculate_distance(
                incident_lat, incident_lon,
                officer['location_lat'], officer['location_lon']
            )
            
            if dist <= radius_km:
                nearby.append({
                    'officer_id': officer['id'],
                    'name': officer['name'],
                    'badge_number': officer['badge_number'],
                    'department': officer['department'],
                    'phone_number': officer['phone_number'],
                    'rank': officer['rank'],
                    'distance_km': round(dist, 2),
                    'latitude': officer['location_lat'],
                    'longitude': officer['location_lon']
                })
        
        # Sort by distance and return top count
        nearby.sort(key=lambda x: x['distance_km'])
        return nearby[:count]
    except Exception as e:
        return [{'error': str(e)}]


def get_officers_by_department(department):
    """Get all active officers in a specific department.
    
    Args:
        department (str): Department name.
    
    Returns:
        list: List of officers in the department.
    """
    try:
        officers = query_db(
            '''SELECT id, name, badge_number, department, phone_number, 
                      email, rank, status, location_lat, location_lon
               FROM officers 
               WHERE department = ? AND status = 'active'
               ORDER BY rank DESC, name ASC''',
            (department,)
        )
        
        return [
            {
                'officer_id': o['id'],
                'name': o['name'],
                'badge_number': o['badge_number'],
                'department': o['department'],
                'phone_number': o['phone_number'],
                'email': o['email'],
                'rank': o['rank'],
                'status': o['status'],
                'latitude': o['location_lat'],
                'longitude': o['location_lon']
            }
            for o in officers
        ]
    except Exception as e:
        return [{'error': str(e)}]


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two points using Haversine formula.
    
    Args:
        lat1, lon1: First point coordinates (degrees).
        lat2, lon2: Second point coordinates (degrees).
    
    Returns:
        float: Distance in kilometers.
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c
