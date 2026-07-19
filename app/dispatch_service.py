"""Dispatch service for incident lifecycle and officer assignment management."""

import math
from datetime import datetime, timedelta
from app.db import query_db, execute_db, get_db
from app.dispatch_audit import log_dispatch_action


def assign_incident_to_officer(incident_id, officer_id, priority=None):
    """Assign an incident to a specific officer.
    
    Args:
        incident_id (int): ID of the incident to assign.
        officer_id (int): ID of the officer to assign.
        priority (str): Priority level ('low', 'medium', 'high', 'critical'). 
                       If None, uses current incident priority.
    
    Returns:
        dict: Assignment details or error dict with 'error' key.
    """
    try:
        # Get incident
        incident = query_db(
            'SELECT * FROM incidents WHERE id = ?',
            (incident_id,),
            one=True
        )
        if not incident:
            return {'error': 'Incident not found'}
        
        # Get officer
        officer = query_db(
            'SELECT * FROM officers WHERE id = ?',
            (officer_id,),
            one=True
        )
        if not officer:
            return {'error': 'Officer not found'}
        
        # Use provided priority or current incident priority
        new_priority = priority or incident['priority_level'] or 'medium'
        
        # Update incident with assignment
        old_priority = incident['priority_level']
        old_status = incident['dispatch_status']
        
        execute_db(
            '''UPDATE incidents 
               SET assigned_officer_id = ?, 
                   assigned_department = ?,
                   dispatch_status = 'assigned',
                   priority_level = ?,
                   dispatch_time = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (officer_id, officer['department'], new_priority, incident_id)
        )
        
        # Create officer assignment
        assignment_id = execute_db(
            '''INSERT INTO officer_assignments 
               (officer_id, incident_id, dispatch_method, dispatch_status)
               VALUES (?, ?, 'dispatch_system', 'pending')''',
            (officer_id, incident_id)
        )
        
        # Log the action
        log_dispatch_action(
            incident_id=incident_id,
            officer_id=officer_id,
            action_type='assign_to_officer',
            status_before=old_status,
            status_after='assigned',
            priority_before=old_priority,
            priority_after=new_priority,
            description=f'Assigned to officer {officer["name"]} ({officer["badge_number"]})'
        )
        
        return {
            'success': True,
            'assignment_id': assignment_id,
            'officer_id': officer_id,
            'incident_id': incident_id,
            'priority': new_priority
        }
    except Exception as e:
        return {'error': str(e)}


def assign_incident_to_department(incident_id, department, priority=None):
    """Assign an incident to a department (not specific officer).
    
    Args:
        incident_id (int): ID of the incident.
        department (str): Department name (e.g., 'traffic', 'patrol', 'emergency').
        priority (str): Priority level.
    
    Returns:
        dict: Assignment details or error dict.
    """
    try:
        incident = query_db(
            'SELECT * FROM incidents WHERE id = ?',
            (incident_id,),
            one=True
        )
        if not incident:
            return {'error': 'Incident not found'}
        
        # Check if department exists
        dept_officers = query_db(
            'SELECT COUNT(*) as count FROM officers WHERE department = ?',
            (department,)
        )
        if not dept_officers or dept_officers[0]['count'] == 0:
            return {'error': 'Department not found or has no officers'}
        
        old_priority = incident['priority_level']
        old_status = incident['dispatch_status']
        new_priority = priority or incident['priority_level'] or 'medium'
        
        execute_db(
            '''UPDATE incidents 
               SET assigned_department = ?,
                   dispatch_status = 'assigned_dept',
                   priority_level = ?,
                   dispatch_time = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (department, new_priority, incident_id)
        )
        
        log_dispatch_action(
            incident_id=incident_id,
            action_type='assign_to_department',
            status_before=old_status,
            status_after='assigned_dept',
            priority_before=old_priority,
            priority_after=new_priority,
            description=f'Assigned to department: {department}'
        )
        
        return {
            'success': True,
            'incident_id': incident_id,
            'department': department,
            'priority': new_priority
        }
    except Exception as e:
        return {'error': str(e)}


def update_incident_status(incident_id, new_status, notes=None):
    """Update incident status and log the change.
    
    Args:
        incident_id (int): ID of the incident.
        new_status (str): New status ('open', 'assigned', 'in_progress', 'resolved', 'closed').
        notes (str): Optional status update notes.
    
    Returns:
        dict: Updated incident details or error dict.
    """
    try:
        incident = query_db(
            'SELECT * FROM incidents WHERE id = ?',
            (incident_id,),
            one=True
        )
        if not incident:
            return {'error': 'Incident not found'}
        
        old_status = incident['dispatch_status']
        
        update_fields = {
            'dispatch_status': new_status,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if notes:
            update_fields['resolution_notes'] = notes
        
        if new_status == 'resolved':
            update_fields['resolved_time'] = datetime.utcnow().isoformat()
        
        set_clause = ', '.join([f'{k} = ?' for k in update_fields.keys()])
        values = list(update_fields.values()) + [incident_id]
        
        execute_db(
            f'UPDATE incidents SET {set_clause} WHERE id = ?',
            tuple(values)
        )
        
        log_dispatch_action(
            incident_id=incident_id,
            action_type='status_update',
            status_before=old_status,
            status_after=new_status,
            description=notes or f'Status changed to {new_status}'
        )
        
        return {
            'success': True,
            'incident_id': incident_id,
            'status': new_status,
            'updated_at': update_fields['updated_at']
        }
    except Exception as e:
        return {'error': str(e)}


def calculate_eta(lat1, lon1, lat2, lon2):
    """Calculate distance and estimated time of arrival using Haversine formula.
    
    Args:
        lat1 (float): Officer latitude.
        lon1 (float): Officer longitude.
        lat2 (float): Incident latitude.
        lon2 (float): Incident longitude.
    
    Returns:
        dict: Contains 'distance_km' and 'eta_minutes' (assuming 40 km/h average speed).
    """
    try:
        distance_km = calculate_distance(lat1, lon1, lat2, lon2)
        # Assume average urban speed of 40 km/h
        eta_minutes = int((distance_km / 40.0) * 60)
        return {
            'distance_km': round(distance_km, 2),
            'eta_minutes': eta_minutes
        }
    except Exception as e:
        return {'error': str(e)}


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


def dispatch_to_officer(officer_id, incident_id):
    """Send dispatch notification to an officer.
    
    Args:
        officer_id (int): Officer to dispatch.
        incident_id (int): Incident to dispatch for.
    
    Returns:
        dict: Dispatch status or error dict.
    """
    try:
        assignment = query_db(
            '''SELECT oa.* FROM officer_assignments oa
               WHERE oa.officer_id = ? AND oa.incident_id = ?''',
            (officer_id, incident_id),
            one=True
        )
        if not assignment:
            return {'error': 'Assignment not found'}
        
        officer = query_db(
            'SELECT * FROM officers WHERE id = ?',
            (officer_id,),
            one=True
        )
        incident = query_db(
            'SELECT * FROM incidents WHERE id = ?',
            (incident_id,),
            one=True
        )
        
        # Calculate ETA if officer has location
        eta_minutes = None
        if officer['location_lat'] and officer['location_lon']:
            eta_result = calculate_eta(
                officer['location_lat'],
                officer['location_lon'],
                incident['latitude'],
                incident['longitude']
            )
            if 'eta_minutes' in eta_result:
                eta_minutes = eta_result['eta_minutes']
        
        # Update assignment dispatch status
        execute_db(
            '''UPDATE officer_assignments 
               SET dispatch_status = 'dispatched',
                   estimated_arrival = datetime('now', '+' || ? || ' minutes')
               WHERE id = ?''',
            (eta_minutes or 10, assignment['id'])
        )
        
        # Log action
        log_dispatch_action(
            incident_id=incident_id,
            officer_id=officer_id,
            action_type='dispatch_sent',
            description=f'Dispatch notification sent to {officer["name"]}'
        )
        
        return {
            'success': True,
            'officer_id': officer_id,
            'incident_id': incident_id,
            'eta_minutes': eta_minutes or 10
        }
    except Exception as e:
        return {'error': str(e)}


def escalate_incident(incident_id, priority):
    """Escalate an incident to a higher priority.
    
    Args:
        incident_id (int): Incident to escalate.
        priority (str): New priority level.
    
    Returns:
        dict: Escalation status or error dict.
    """
    try:
        incident = query_db(
            'SELECT * FROM incidents WHERE id = ?',
            (incident_id,),
            one=True
        )
        if not incident:
            return {'error': 'Incident not found'}
        
        old_priority = incident['priority_level']
        
        execute_db(
            '''UPDATE incidents 
               SET priority_level = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (priority, incident_id)
        )
        
        log_dispatch_action(
            incident_id=incident_id,
            action_type='escalate',
            priority_before=old_priority,
            priority_after=priority,
            description=f'Incident escalated from {old_priority} to {priority}'
        )
        
        return {
            'success': True,
            'incident_id': incident_id,
            'old_priority': old_priority,
            'new_priority': priority
        }
    except Exception as e:
        return {'error': str(e)}


def mark_incident_resolved(incident_id, notes=None):
    """Mark an incident as resolved.
    
    Args:
        incident_id (int): Incident to resolve.
        notes (str): Resolution notes.
    
    Returns:
        dict: Resolution status or error dict.
    """
    try:
        incident = query_db(
            'SELECT * FROM incidents WHERE id = ?',
            (incident_id,),
            one=True
        )
        if not incident:
            return {'error': 'Incident not found'}
        
        execute_db(
            '''UPDATE incidents 
               SET dispatch_status = 'resolved',
                   resolved_time = CURRENT_TIMESTAMP,
                   resolution_notes = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (notes or '', incident_id)
        )
        
        log_dispatch_action(
            incident_id=incident_id,
            action_type='resolve',
            status_before=incident['dispatch_status'],
            status_after='resolved',
            description=notes or 'Incident marked as resolved'
        )
        
        return {
            'success': True,
            'incident_id': incident_id,
            'resolved_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {'error': str(e)}
