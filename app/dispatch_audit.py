"""Audit logging for dispatch actions and incident lifecycle changes."""

from datetime import datetime, timedelta
from app.db import query_db, execute_db


def log_dispatch_action(incident_id, officer_id=None, action_type=None,
                       status_before=None, status_after=None,
                       priority_before=None, priority_after=None,
                       performed_by=None, description=None):
    """Log a dispatch action to the audit trail.
    
    Args:
        incident_id (int): Incident being acted upon.
        officer_id (int): Officer involved (if applicable).
        action_type (str): Type of action ('assign_to_officer', 'escalate', etc.).
        status_before (str): Previous status.
        status_after (str): New status.
        priority_before (str): Previous priority.
        priority_after (str): New priority.
        performed_by (str): User/system that performed the action.
        description (str): Human-readable description.
    
    Returns:
        dict: Log entry ID or error dict.
    """
    try:
        log_id = execute_db(
            '''INSERT INTO dispatch_logs 
               (incident_id, officer_id, action_type, status_before, status_after,
                priority_before, priority_after, performed_by, description, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
            (incident_id, officer_id, action_type, status_before, status_after,
             priority_before, priority_after, performed_by or 'system', description)
        )
        
        return {'success': True, 'log_id': log_id}
    except Exception as e:
        return {'error': str(e)}


def get_incident_audit_trail(incident_id):
    """Get the complete audit trail for an incident.
    
    Args:
        incident_id (int): Incident ID.
    
    Returns:
        list: Audit log entries sorted by timestamp (newest first).
    """
    try:
        logs = query_db(
            '''SELECT 
                   id, incident_id, officer_id, action_type, 
                   status_before, status_after, priority_before, priority_after,
                   performed_by, timestamp, description
               FROM dispatch_logs
               WHERE incident_id = ?
               ORDER BY timestamp DESC''',
            (incident_id,)
        )
        
        return [
            {
                'log_id': log['id'],
                'incident_id': log['incident_id'],
                'officer_id': log['officer_id'],
                'action_type': log['action_type'],
                'status_before': log['status_before'],
                'status_after': log['status_after'],
                'priority_before': log['priority_before'],
                'priority_after': log['priority_after'],
                'performed_by': log['performed_by'],
                'timestamp': log['timestamp'],
                'description': log['description']
            }
            for log in logs
        ]
    except Exception as e:
        return [{'error': str(e)}]


def get_officer_activity_log(officer_id, days=7):
    """Get activity log for an officer over the past N days.
    
    Args:
        officer_id (int): Officer ID.
        days (int): Number of days to look back (default 7).
    
    Returns:
        list: Activity log entries sorted by timestamp (newest first).
    """
    try:
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        logs = query_db(
            '''SELECT 
                   id, incident_id, officer_id, action_type,
                   status_before, status_after, priority_before, priority_after,
                   performed_by, timestamp, description
               FROM dispatch_logs
               WHERE officer_id = ? AND timestamp > ?
               ORDER BY timestamp DESC''',
            (officer_id, cutoff_date)
        )
        
        return [
            {
                'log_id': log['id'],
                'incident_id': log['incident_id'],
                'officer_id': log['officer_id'],
                'action_type': log['action_type'],
                'status_before': log['status_before'],
                'status_after': log['status_after'],
                'priority_before': log['priority_before'],
                'priority_after': log['priority_after'],
                'performed_by': log['performed_by'],
                'timestamp': log['timestamp'],
                'description': log['description']
            }
            for log in logs
        ]
    except Exception as e:
        return [{'error': str(e)}]
