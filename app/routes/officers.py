"""REST API endpoints for officer management."""

from flask import Blueprint, request, jsonify
from app.db import query_db, execute_db
from app.officer_location_service import (
    update_officer_location, get_officer_location, find_nearest_officers
)

officers_bp = Blueprint('officers', __name__, url_prefix='/api/v1/officers')


@officers_bp.route('', methods=['GET'])
def list_officers():
    """Get all active officers, optionally filtered by department.
    
    Query params:
    - department: str (optional)
    - status: str (optional, default 'active')
    """
    try:
        department = request.args.get('department')
        status = request.args.get('status', 'active')
        
        query = 'SELECT * FROM officers WHERE status = ?'
        params = [status]
        
        if department:
            query += ' AND department = ?'
            params.append(department)
        
        query += ' ORDER BY name ASC'
        
        officers = query_db(query, tuple(params))
        
        result = [
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
                'longitude': o['location_lon'],
                'created_at': o['created_at'],
                'updated_at': o['updated_at']
            }
            for o in officers
        ]
        
        return jsonify({
            'total': len(result),
            'officers': result
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@officers_bp.route('', methods=['POST'])
def create_officer():
    """Create a new officer record.
    
    Expected JSON:
    {
        'name': str,
        'badge_number': str,
        'department': str,
        'phone_number': str (optional),
        'email': str (optional),
        'rank': str (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'badge_number' not in data or 'department' not in data:
            return jsonify({'error': 'Missing required fields: name, badge_number, department'}), 400
        
        # Check if badge_number already exists
        existing = query_db(
            'SELECT id FROM officers WHERE badge_number = ?',
            (data['badge_number'],),
            one=True
        )
        if existing:
            return jsonify({'error': 'Badge number already exists'}), 400
        
        officer_id = execute_db(
            '''INSERT INTO officers 
               (name, badge_number, department, phone_number, email, rank, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)''',
            (data['name'], data['badge_number'], data['department'],
             data.get('phone_number'), data.get('email'), data.get('rank'))
        )
        
        return jsonify({
            'success': True,
            'officer_id': officer_id,
            'message': 'Officer created successfully'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@officers_bp.route('/<int:officer_id>', methods=['GET'])
def get_officer(officer_id):
    """Get details for a specific officer.
    
    Returns: Officer details including current location.
    """
    try:
        officer = query_db(
            'SELECT * FROM officers WHERE id = ?',
            (officer_id,),
            one=True
        )
        
        if not officer:
            return jsonify({'error': 'Officer not found'}), 404
        
        return jsonify({
            'officer_id': officer['id'],
            'name': officer['name'],
            'badge_number': officer['badge_number'],
            'department': officer['department'],
            'phone_number': officer['phone_number'],
            'email': officer['email'],
            'rank': officer['rank'],
            'status': officer['status'],
            'latitude': officer['location_lat'],
            'longitude': officer['location_lon'],
            'created_at': officer['created_at'],
            'updated_at': officer['updated_at']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@officers_bp.route('/<int:officer_id>', methods=['PUT'])
def update_officer(officer_id):
    """Update officer details.
    
    Expected JSON: Any of the officer fields (name, email, phone_number, rank, status)
    """
    try:
        data = request.get_json()
        
        officer = query_db(
            'SELECT id FROM officers WHERE id = ?',
            (officer_id,),
            one=True
        )
        if not officer:
            return jsonify({'error': 'Officer not found'}), 404
        
        # Build update query dynamically
        updatable_fields = ['name', 'email', 'phone_number', 'rank', 'status']
        updates = {k: v for k, v in data.items() if k in updatable_fields}
        
        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        updates['updated_at'] = 'CURRENT_TIMESTAMP'
        
        set_clause = ', '.join([f'{k} = ?' if k != 'updated_at' else f'{k} = {k}' 
                               for k in updates.keys()])
        values = [v for k, v in updates.items() if k != 'updated_at'] + [officer_id]
        
        execute_db(
            f'UPDATE officers SET {set_clause} WHERE id = ?',
            tuple(values)
        )
        
        return jsonify({
            'success': True,
            'officer_id': officer_id,
            'message': 'Officer updated successfully'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@officers_bp.route('/<int:officer_id>/location', methods=['POST'])
def update_location(officer_id):
    """Update officer's current location.
    
    Expected JSON:
    {
        'latitude': float,
        'longitude': float
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'latitude' not in data or 'longitude' not in data:
            return jsonify({'error': 'Missing required fields: latitude, longitude'}), 400
        
        result = update_officer_location(officer_id, data['latitude'], data['longitude'])
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@officers_bp.route('/nearby', methods=['GET'])
def nearby_officers():
    """Find nearest officers to a location.
    
    Query params:
    - latitude: float (required)
    - longitude: float (required)
    - count: int (optional, default 3)
    - radius_km: float (optional, default 5)
    """
    try:
        lat = request.args.get('latitude', type=float)
        lon = request.args.get('longitude', type=float)
        count = request.args.get('count', 3, type=int)
        radius_km = request.args.get('radius_km', 5, type=float)
        
        if lat is None or lon is None:
            return jsonify({'error': 'Missing required params: latitude, longitude'}), 400
        
        nearby = find_nearest_officers(lat, lon, count, radius_km)
        
        return jsonify({
            'incident_location': {'latitude': lat, 'longitude': lon},
            'search_radius_km': radius_km,
            'nearby_officers': nearby
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@officers_bp.route('/<int:officer_id>', methods=['DELETE'])
def delete_officer(officer_id):
    """Deactivate an officer (soft delete by setting status to 'inactive').
    
    Note: Uses soft delete to preserve audit trail.
    """
    try:
        officer = query_db(
            'SELECT id FROM officers WHERE id = ?',
            (officer_id,),
            one=True
        )
        if not officer:
            return jsonify({'error': 'Officer not found'}), 404
        
        execute_db(
            '''UPDATE officers 
               SET status = 'inactive', updated_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (officer_id,)
        )
        
        return jsonify({
            'success': True,
            'officer_id': officer_id,
            'message': 'Officer deactivated'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
