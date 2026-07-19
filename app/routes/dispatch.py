"""REST API endpoints for dispatch management and incident lifecycle."""

from flask import Blueprint, request, jsonify
from app.db import query_db
from app.dispatch_service import (
    assign_incident_to_officer, assign_incident_to_department,
    update_incident_status, dispatch_to_officer, escalate_incident,
    mark_incident_resolved
)
from app.dispatch_audit import get_incident_audit_trail

dispatch_bp = Blueprint('dispatch', __name__, url_prefix='/api/v1/dispatch')


@dispatch_bp.route('/assign-to-officer', methods=['POST'])
def assign_to_officer():
    """Assign an incident to a specific officer.
    
    Expected JSON:
    {
        'incident_id': int,
        'officer_id': int,
        'priority': str (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'incident_id' not in data or 'officer_id' not in data:
            return jsonify({'error': 'Missing required fields: incident_id, officer_id'}), 400
        
        result = assign_incident_to_officer(
            data['incident_id'],
            data['officer_id'],
            data.get('priority')
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_bp.route('/assign-to-department', methods=['POST'])
def assign_to_department():
    """Assign an incident to a department.
    
    Expected JSON:
    {
        'incident_id': int,
        'department': str,
        'priority': str (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'incident_id' not in data or 'department' not in data:
            return jsonify({'error': 'Missing required fields: incident_id, department'}), 400
        
        result = assign_incident_to_department(
            data['incident_id'],
            data['department'],
            data.get('priority')
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_bp.route('/incidents/<int:incident_id>/status', methods=['PUT'])
def update_status(incident_id):
    """Update incident status.
    
    Expected JSON:
    {
        'status': str,
        'notes': str (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'error': 'Missing required field: status'}), 400
        
        result = update_incident_status(
            incident_id,
            data['status'],
            data.get('notes')
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_bp.route('/incidents/<int:incident_id>/priority', methods=['PUT'])
def update_priority(incident_id):
    """Update incident priority level.
    
    Expected JSON:
    {
        'priority': str ('low', 'medium', 'high', 'critical')
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'priority' not in data:
            return jsonify({'error': 'Missing required field: priority'}), 400
        
        result = escalate_incident(incident_id, data['priority'])
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_bp.route('/incidents/<int:incident_id>/status', methods=['GET'])
def get_status(incident_id):
    """Get current incident dispatch status.
    
    Returns detailed status information including:
    - dispatch_status, priority_level, assigned_officer_id, assigned_department
    - dispatch_time, resolved_time, resolution_notes
    """
    try:
        incident = query_db(
            '''SELECT id, dispatch_status, priority_level, assigned_officer_id,
                      assigned_department, dispatch_time, resolved_time, resolution_notes,
                      eta_minutes, created_at, updated_at
               FROM incidents WHERE id = ?''',
            (incident_id,),
            one=True
        )
        
        if not incident:
            return jsonify({'error': 'Incident not found'}), 404
        
        return jsonify({
            'incident_id': incident['id'],
            'dispatch_status': incident['dispatch_status'],
            'priority_level': incident['priority_level'],
            'assigned_officer_id': incident['assigned_officer_id'],
            'assigned_department': incident['assigned_department'],
            'dispatch_time': incident['dispatch_time'],
            'resolved_time': incident['resolved_time'],
            'resolution_notes': incident['resolution_notes'],
            'eta_minutes': incident['eta_minutes'],
            'created_at': incident['created_at'],
            'updated_at': incident['updated_at']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_bp.route('/incidents/<int:incident_id>/audit-trail', methods=['GET'])
def get_audit_trail(incident_id):
    """Get complete audit trail for an incident.
    
    Returns chronological list of all dispatch actions and status changes.
    """
    try:
        # Verify incident exists
        incident = query_db(
            'SELECT id FROM incidents WHERE id = ?',
            (incident_id,),
            one=True
        )
        
        if not incident:
            return jsonify({'error': 'Incident not found'}), 404
        
        trail = get_incident_audit_trail(incident_id)
        
        return jsonify({
            'incident_id': incident_id,
            'audit_trail': trail
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_bp.route('/incidents/<int:incident_id>/resolve', methods=['POST'])
def resolve_incident(incident_id):
    """Mark an incident as resolved.
    
    Expected JSON:
    {
        'notes': str (optional)
    }
    """
    try:
        data = request.get_json() or {}
        
        result = mark_incident_resolved(incident_id, data.get('notes'))
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
