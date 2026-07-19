"""REST API endpoints for dispatch queue management and reporting."""

from flask import Blueprint, request, jsonify
from app.db import query_db, execute_db
from app.dispatch_service import assign_incident_to_officer

dispatch_mgmt_bp = Blueprint('dispatch_management', __name__, url_prefix='/api/v1/dispatch')


@dispatch_mgmt_bp.route('/queue', methods=['GET'])
def dispatch_queue():
    """Get the current dispatch queue of unassigned/pending incidents.
    
    Query params:
    - status: str (optional, default 'open')
    - priority: str (optional, filters by priority)
    - limit: int (optional, default 50)
    """
    try:
        status = request.args.get('status', 'open')
        priority = request.args.get('priority')
        limit = request.args.get('limit', 50, type=int)
        
        query = '''SELECT id, incident_type, severity_level, latitude, longitude,
                          priority_level, dispatch_status, assigned_officer_id,
                          created_at, updated_at
                   FROM incidents
                   WHERE dispatch_status IN ('open', 'assigned_dept')'''
        params = []
        
        if status:
            query += ' AND dispatch_status = ?'
            params.append(status)
        
        if priority:
            query += ' AND priority_level = ?'
            params.append(priority)
        
        query += ' ORDER BY priority_level DESC, created_at ASC LIMIT ?'
        params.append(limit)
        
        incidents = query_db(query, tuple(params))
        
        result = [
            {
                'incident_id': i['id'],
                'incident_type': i['incident_type'],
                'severity_level': i['severity_level'],
                'priority_level': i['priority_level'],
                'dispatch_status': i['dispatch_status'],
                'location': {'latitude': i['latitude'], 'longitude': i['longitude']},
                'assigned_officer_id': i['assigned_officer_id'],
                'created_at': i['created_at'],
                'updated_at': i['updated_at']
            }
            for i in incidents
        ]
        
        return jsonify({
            'queue_size': len(result),
            'incidents': result
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_mgmt_bp.route('/assignments/<int:officer_id>', methods=['GET'])
def officer_assignments(officer_id):
    """Get all current assignments for an officer.
    
    Query params:
    - status: str (optional, filters by assignment dispatch_status)
    """
    try:
        status = request.args.get('status')
        
        query = '''SELECT oa.id, oa.incident_id, oa.dispatch_status, oa.assignment_time,
                          oa.estimated_arrival, oa.actual_arrival, i.incident_type,
                          i.severity_level, i.priority_level, i.latitude, i.longitude
                   FROM officer_assignments oa
                   JOIN incidents i ON oa.incident_id = i.id
                   WHERE oa.officer_id = ?'''
        params = [officer_id]
        
        if status:
            query += ' AND oa.dispatch_status = ?'
            params.append(status)
        
        query += ' ORDER BY oa.assignment_time DESC'
        
        assignments = query_db(query, tuple(params))
        
        result = [
            {
                'assignment_id': a['id'],
                'incident_id': a['incident_id'],
                'incident_type': a['incident_type'],
                'severity_level': a['severity_level'],
                'priority_level': a['priority_level'],
                'dispatch_status': a['dispatch_status'],
                'location': {'latitude': a['latitude'], 'longitude': a['longitude']},
                'assignment_time': a['assignment_time'],
                'estimated_arrival': a['estimated_arrival'],
                'actual_arrival': a['actual_arrival']
            }
            for a in assignments
        ]
        
        return jsonify({
            'officer_id': officer_id,
            'assignment_count': len(result),
            'assignments': result
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_mgmt_bp.route('/statistics', methods=['GET'])
def dispatch_statistics():
    """Get dispatch statistics and metrics.
    
    Returns counts for: open incidents, assigned incidents, in_progress, resolved,
    and average dispatch time.
    """
    try:
        stats = {}
        
        # Count by status
        for status in ['open', 'assigned', 'assigned_dept', 'in_progress', 'resolved']:
            count = query_db(
                'SELECT COUNT(*) as count FROM incidents WHERE dispatch_status = ?',
                (status,),
                one=True
            )
            stats[f'{status}_count'] = count['count']
        
        # Get average ETA
        avg_eta = query_db(
            'SELECT AVG(eta_minutes) as avg FROM incidents WHERE eta_minutes IS NOT NULL',
            one=True
        )
        stats['average_eta_minutes'] = avg_eta['avg'] or 0
        
        # Count by priority
        priorities = query_db(
            '''SELECT priority_level, COUNT(*) as count 
               FROM incidents 
               WHERE dispatch_status != 'resolved'
               GROUP BY priority_level'''
        )
        
        stats['by_priority'] = {p['priority_level']: p['count'] for p in priorities}
        
        # Active officers
        active_officers = query_db(
            'SELECT COUNT(*) as count FROM officers WHERE status = "active"',
            one=True
        )
        stats['active_officers'] = active_officers['count']
        
        # Count assignments by status
        assignment_stats = query_db(
            '''SELECT dispatch_status, COUNT(*) as count 
               FROM officer_assignments 
               GROUP BY dispatch_status'''
        )
        stats['assignments_by_status'] = {a['dispatch_status']: a['count'] for a in assignment_stats}
        
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_mgmt_bp.route('/bulk-assign', methods=['POST'])
def bulk_assign():
    """Bulk assign multiple incidents to a department or find optimal officers.
    
    Expected JSON:
    {
        'incident_ids': [int, ...],
        'department': str (optional),
        'priority': str (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'incident_ids' not in data:
            return jsonify({'error': 'Missing required field: incident_ids'}), 400
        
        incident_ids = data['incident_ids']
        department = data.get('department')
        priority = data.get('priority')
        
        if not isinstance(incident_ids, list):
            return jsonify({'error': 'incident_ids must be a list'}), 400
        
        results = []
        for incident_id in incident_ids:
            if department:
                # Assign to department
                query = 'SELECT id FROM officers WHERE department = ? AND status = "active" LIMIT 1'
                officer = query_db(query, (department,), one=True)
                
                if officer:
                    result = assign_incident_to_officer(incident_id, officer['id'], priority)
                    results.append({'incident_id': incident_id, **result})
            else:
                results.append({'incident_id': incident_id, 'status': 'skipped'})
        
        return jsonify({
            'total': len(incident_ids),
            'assigned': sum(1 for r in results if r.get('success')),
            'results': results
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_mgmt_bp.route('/reassign', methods=['POST'])
def reassign():
    """Reassign an incident from one officer to another.
    
    Expected JSON:
    {
        'incident_id': int,
        'from_officer_id': int,
        'to_officer_id': int,
        'reason': str (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'incident_id' not in data or 'to_officer_id' not in data:
            return jsonify({'error': 'Missing required fields: incident_id, to_officer_id'}), 400
        
        incident_id = data['incident_id']
        to_officer_id = data['to_officer_id']
        reason = data.get('reason', 'Reassigned by dispatcher')
        
        # Get current assignment
        incident = query_db(
            'SELECT assigned_officer_id FROM incidents WHERE id = ?',
            (incident_id,),
            one=True
        )
        
        if not incident:
            return jsonify({'error': 'Incident not found'}), 404
        
        # Log old assignment as ended
        if incident['assigned_officer_id']:
            execute_db(
                '''UPDATE officer_assignments 
                   SET dispatch_status = 'reassigned'
                   WHERE officer_id = ? AND incident_id = ?''',
                (incident['assigned_officer_id'], incident_id)
            )
        
        # Assign to new officer
        result = assign_incident_to_officer(incident_id, to_officer_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify({
            'success': True,
            'incident_id': incident_id,
            'from_officer_id': incident['assigned_officer_id'],
            'to_officer_id': to_officer_id,
            'reason': reason
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dispatch_mgmt_bp.route('/reports/performance', methods=['GET'])
def performance_report():
    """Generate dispatch performance report.
    
    Query params:
    - days: int (optional, default 7) - days to look back
    - officer_id: int (optional) - filter by specific officer
    """
    try:
        days = request.args.get('days', 7, type=int)
        officer_id = request.args.get('officer_id', type=int)
        
        cutoff_date = f"datetime('now', '-{days} days')"
        
        # Get resolved incidents
        query = f'''SELECT COUNT(*) as resolved_count, 
                           AVG(CAST((julianday(resolved_time) - julianday(dispatch_time)) * 24 * 60 AS REAL)) as avg_resolution_minutes
                    FROM incidents
                    WHERE dispatch_status = 'resolved' 
                    AND resolved_time > {cutoff_date}'''
        
        if officer_id:
            query += f' AND assigned_officer_id = {officer_id}'
        
        resolved_stats = query_db(query, one=True)
        
        # Get dispatch performance by priority
        query = f'''SELECT priority_level, COUNT(*) as count,
                           AVG(CAST((julianday(resolved_time) - julianday(dispatch_time)) * 24 * 60 AS REAL)) as avg_resolution_minutes
                    FROM incidents
                    WHERE dispatch_status = 'resolved'
                    AND resolved_time > {cutoff_date}'''
        
        if officer_id:
            query += f' AND assigned_officer_id = {officer_id}'
        
        query += ' GROUP BY priority_level'
        
        by_priority = query_db(query)
        
        return jsonify({
            'period_days': days,
            'officer_id': officer_id,
            'resolved_count': resolved_stats['resolved_count'],
            'avg_resolution_minutes': round(resolved_stats['avg_resolution_minutes'] or 0, 2),
            'by_priority': [
                {
                    'priority': p['priority_level'],
                    'count': p['count'],
                    'avg_resolution_minutes': round(p['avg_resolution_minutes'] or 0, 2)
                }
                for p in by_priority
            ]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
