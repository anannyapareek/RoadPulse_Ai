"""Main Flask application for RoadPulse AI."""

import os
from dotenv import load_dotenv
load_dotenv()
import json
from datetime import datetime
from flask import (
    Flask, request, jsonify, render_template_string, render_template,
    redirect, url_for, session, g
)
from werkzeug.exceptions import BadRequest

from app import create_app
from app.db import get_db, execute_db, query_db, init_db
from app.services.gemini_service import classify_image, generate_report_summary
from app.utils.duplicate import find_duplicate
from app.utils.scoring import compute_confidence, get_severity_ordinal, get_severity_color
from app.utils.routing_rules import get_routing_rule
from app.utils.utils import (
    save_uploaded_image, generate_device_id, validate_device_id,
    truncate_string, format_timestamp
)

# ── New feature modules ──────────────────────────────────────────────────────
from app.routes.community_validation import validation_bp
from app.routes.dashboard import dashboard_bp
from app.routes.smart_route import smart_route_bp
from app.routes.dispatch import dispatch_bp
from app.routes.officers import officers_bp
from app.routes.dispatch_management import dispatch_mgmt_bp
from app.integrations.emergency_call import emergency_bp, trigger_emergency_call
from app.utils.xai import explain_confidence, combine_with_gemini_reason
from app.utils.knowledge_db import start_scheduler
from app.notification_service import process_notification_queue


# Create Flask app
app = create_app()

# Register new Blueprints
app.register_blueprint(validation_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(smart_route_bp)
app.register_blueprint(emergency_bp)
app.register_blueprint(dispatch_bp)
app.register_blueprint(officers_bp)
app.register_blueprint(dispatch_mgmt_bp)


# ============================================================================
# SETUP & INITIALIZATION
# ============================================================================

@app.before_request
def before_request():
    """Initialize request context."""
    g.upload_folder = os.path.join(os.getcwd(), 'uploads')
    if not os.path.exists(g.upload_folder):
        os.makedirs(g.upload_folder)


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/report', methods=['POST'])
def api_report():
    """Submit a new road incident report with image.
    
    Expected multipart form data:
    - image: image file (required)
    - lat: latitude (required)
    - lon: longitude (required)
    - gps_accuracy: GPS accuracy in meters (optional, default 25.0)
    - note: user note (optional)
    - device_id: device identifier (optional, generated if not provided)
    
    Returns:
        JSON: {
            'success': bool,
            'incident_id': int (if success),
            'error': str (if not success),
            'classification': dict,
            'confidence': float,
            'is_duplicate': bool
        }
    """
    try:
        # Validate request format
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400
        
        # Extract form fields
        image_file = request.files['image']
        
        try:
            latitude = float(request.form.get('lat', 0))
            longitude = float(request.form.get('lon', 0))
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Invalid latitude or longitude'
            }), 400
        
        gps_accuracy = request.form.get('gps_accuracy', '25.0')
        try:
            gps_accuracy = float(gps_accuracy)
        except (ValueError, TypeError):
            gps_accuracy = 25.0
        
        note = request.form.get('note', '').strip()
        device_id = request.form.get('device_id', '').strip()
        
        # Generate or validate device_id
        if not device_id:
            device_id = generate_device_id()
        elif not validate_device_id(device_id):
            return jsonify({
                'success': False,
                'error': 'Invalid device_id format'
            }), 400
        
        # Save uploaded image
        image_filename, image_path = save_uploaded_image(
            image_file,
            g.upload_folder
        )
        
        # Classify image using Gemini
        try:
            classification, raw_response = classify_image(image_path, note)
        except Exception as e:
            # Still record the incident even if classification fails
            classification = {
                'incident_type': 'other',
                'severity_level': 'low',
                'confidence_score': 0.2,
                'reason': f'Classification failed: {str(e)}'
            }
            raw_response = str(e)
        
        incident_type = classification.get('incident_type', 'other')
        severity_level = classification.get('severity_level', 'low')
        gemini_confidence = classification.get('confidence_score', 0.0)
        
        # Check for duplicates
        db = get_db()
        existing = query_db(
            'SELECT id, latitude, longitude, incident_type FROM incidents WHERE is_duplicate = 0'
        )
        
        duplicate_info = find_duplicate(
            latitude, longitude, incident_type,
            [dict(r) for r in existing]
        )
        
        is_duplicate = duplicate_info is not None
        
        # Compute final confidence (now passes device_id for trust-score integration)
        final_confidence = compute_confidence(
            gemini_confidence,
            gps_accuracy,
            is_duplicate,
            device_id=device_id,
            incident_type=incident_type,
        )

        # Build features dict for SHAP explanation (mirrors scoring.py feature order)
        from app.utils.scoring import encode_incident_type as _enc
        from app.utils.trust_score import get_trust_score as _trust
        _conf_features = {
            "base_score": float(max(0.0, min(1.0, gemini_confidence))),
            "gps_accuracy_factor": max(0.5, min(1.0, 100.0 / max(gps_accuracy, 1.0))),
            "duplicate_factor": 0.7 if is_duplicate else 1.0,
            "device_trust_score": _trust(device_id),
            "hour_of_day": datetime.utcnow().hour,
            "image_validation_passed": 1.0,
            "incident_type_code": _enc(incident_type),
        }
        _shap_result = explain_confidence(_conf_features)
        _gemini_reason = classification.get('reason', '')
        _explanation = combine_with_gemini_reason(_shap_result, _gemini_reason)
        
        # Register device if new
        device_check = query_db(
            'SELECT id FROM devices WHERE device_id = ?',
            (device_id,),
            one=True
        )
        
        if not device_check:
            execute_db(
                'INSERT INTO devices (device_id, device_name, last_seen, total_reports, is_active) '
                'VALUES (?, ?, ?, ?, ?)',
                (device_id, f'Device {device_id[:8]}', datetime.utcnow().isoformat(), 1, 1)
            )
        else:
            execute_db(
                'UPDATE devices SET last_seen = ?, total_reports = total_reports + 1 '
                'WHERE device_id = ?',
                (datetime.utcnow().isoformat(), device_id)
            )
        
        def get_ward(lat, lon):
            # Simple quadrant based assignment for the MVP
            if lat > 28.61:
                return 'Ward 1 (North)' if lon < 77.21 else 'Ward 3 (East)'
            else:
                return 'Ward 4 (West)' if lon < 77.21 else 'Ward 2 (South)'

        assigned_ward = get_ward(latitude, longitude)

        # Insert incident into database
        incident_id = execute_db(
            'INSERT INTO incidents '
            '(device_id, latitude, longitude, gps_accuracy, incident_type, severity_level, '
            'confidence_score, notes, image_filename, raw_gemini_response, is_duplicate, status, ward) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                device_id, latitude, longitude, gps_accuracy,
                incident_type, severity_level, final_confidence,
                note, image_filename, raw_response, 1 if is_duplicate else 0,
                'pending', assigned_ward
            )
        )
        
        # If duplicate, link to original
        if duplicate_info:
            original_id, dist_km, dist_m = duplicate_info
            execute_db(
                'UPDATE incidents SET duplicate_of_id = ? WHERE id = ?',
                (original_id, incident_id)
            )
        
        # Fire emergency call if high-severity + high-confidence
        location_desc = note or f"{latitude:.4f},{longitude:.4f}"
        try:
            trigger_emergency_call(incident_id, incident_type, location_desc, final_confidence)
        except Exception as e:
            print(f"Emergency call failed (non-fatal): {e}")

        return jsonify({
            'success': True,
            'incident_id': incident_id,
            'classification': classification,
            'confidence': final_confidence,
            'is_duplicate': is_duplicate,
            'device_id': device_id,
            'explanation': _explanation,
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@app.route('/api/incidents', methods=['GET'])
def api_incidents():
    """Fetch incident list with optional filtering.
    
    Query parameters:
    - limit: max results (default 100)
    - offset: pagination offset (default 0)
    - type: filter by incident type
    - severity: filter by severity level
    - include_duplicates: include flagged duplicates (default false)
    
    Returns:
        JSON: {
            'success': bool,
            'incidents': [list of incident dicts],
            'total': int,
            'count': int
        }
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        incident_type = request.args.get('type', '', type=str).strip()
        severity = request.args.get('severity', '', type=str).strip()
        include_dups = request.args.get('include_duplicates', 'false', type=str).lower() == 'true'
        
        # Build query
        base_query = 'SELECT * FROM incidents WHERE 1=1'
        count_query = 'SELECT COUNT(*) as total FROM incidents WHERE 1=1'
        params = []
        
        if not include_dups:
            base_query += ' AND is_duplicate = 0'
            count_query += ' AND is_duplicate = 0'
        
        if incident_type:
            base_query += ' AND incident_type = ?'
            count_query += ' AND incident_type = ?'
            params.append(incident_type)
        
        if severity:
            base_query += ' AND severity_level = ?'
            count_query += ' AND severity_level = ?'
            params.append(severity)
        
        # Get total count
        total_result = query_db(count_query, params, one=True)
        total_count = dict(total_result)['total'] if total_result else 0
        
        # Fetch paginated results, sorted by date descending
        base_query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        rows = query_db(base_query, params)
        
        incidents = []
        for row in rows:
            incident_dict = dict(row)
            # Format for JSON response
            incident_dict['routing_rule'] = get_routing_rule(incident_dict['incident_type'])
            incident_dict['severity_color'] = get_severity_color(incident_dict['severity_level'])
            incidents.append(incident_dict)
        
        return jsonify({
            'success': True,
            'incidents': incidents,
            'total': total_count,
            'count': len(incidents)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Fetch aggregated statistics about incidents.
    
    Returns:
        JSON: {
            'success': bool,
            'stats': {
                'total_incidents': int,
                'total_devices': int,
                'incidents_by_type': dict,
                'incidents_by_severity': dict,
                'average_confidence': float,
                'duplicate_count': int
            }
        }
    """
    try:
        db = get_db()
        
        # Total incidents (non-duplicates)
        total_result = query_db(
            'SELECT COUNT(*) as count FROM incidents WHERE is_duplicate = 0',
            one=True
        )
        total_incidents = dict(total_result)['count'] if total_result else 0
        
        # Total active devices
        devices_result = query_db(
            'SELECT COUNT(*) as count FROM devices WHERE is_active = 1',
            one=True
        )
        total_devices = dict(devices_result)['count'] if devices_result else 0
        
        # Incidents by type
        type_results = query_db(
            'SELECT incident_type, COUNT(*) as count FROM incidents '
            'WHERE is_duplicate = 0 GROUP BY incident_type'
        )
        incidents_by_type = {
            dict(r)['incident_type']: dict(r)['count'] for r in type_results
        }
        
        # Incidents by severity
        severity_results = query_db(
            'SELECT severity_level, COUNT(*) as count FROM incidents '
            'WHERE is_duplicate = 0 GROUP BY severity_level'
        )
        incidents_by_severity = {
            dict(r)['severity_level']: dict(r)['count'] for r in severity_results
        }
        
        # Average confidence score
        confidence_result = query_db(
            'SELECT AVG(confidence_score) as avg_confidence FROM incidents '
            'WHERE is_duplicate = 0',
            one=True
        )
        average_confidence = (
            dict(confidence_result)['avg_confidence'] if confidence_result else 0.0
        )
        
        # Duplicate count
        dup_result = query_db(
            'SELECT COUNT(*) as count FROM incidents WHERE is_duplicate = 1',
            one=True
        )
        duplicate_count = dict(dup_result)['count'] if dup_result else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'total_incidents': total_incidents,
                'total_devices': total_devices,
                'incidents_by_type': incidents_by_type,
                'incidents_by_severity': incidents_by_severity,
                'average_confidence': round(average_confidence, 3) if average_confidence else 0.0,
                'duplicate_count': duplicate_count
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


# ============================================================================
# STATIC/UI ROUTES
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """Root route: serve the main RoadPulse frontend.
    
    Returns:
        HTML: Rendered console.html template.
    """
    return render_template('console.html')


@app.route('/admin', methods=['GET'])
def admin():
    """Admin dashboard: display incidents and statistics.
    
    Returns:
        HTML: Rendered admin.html template.
    """
    return render_template('admin.html')


@app.route('/uploads/<filename>', methods=['GET'])
def serve_upload(filename):
    """Serve uploaded images from the uploads folder."""
    from flask import send_from_directory
    return send_from_directory(os.path.join(os.getcwd(), 'uploads'), filename)


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Return dashboard analytics metrics."""
    try:
        # 1. Resolution timelines (Average hours to resolve)
        # 2. Complaints pending for more than 60 days
        # 3. Ward-level infrastructure quality
        # 4. Response performance (e.g. % resolved under 24 hours)

        # Average resolution time in hours
        avg_res_row = query_db('''
            SELECT AVG((julianday(resolved_at) - julianday(created_at)) * 24) as avg_hours 
            FROM incidents 
            WHERE status = 'resolved' AND resolved_at IS NOT NULL
        ''', one=True)
        avg_resolution_hours = round(avg_res_row['avg_hours'] or 0, 1)

        # Pending > 60 days
        pending_60_row = query_db('''
            SELECT COUNT(*) as count 
            FROM incidents 
            WHERE status = 'pending' AND created_at < datetime('now', '-60 days')
        ''', one=True)
        pending_60_days = pending_60_row['count']

        # Ward-level quality (Count of active/pending vs resolved per ward)
        ward_rows = query_db('''
            SELECT ward, 
                   SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending_count,
                   SUM(CASE WHEN status='resolved' THEN 1 ELSE 0 END) as resolved_count
            FROM incidents
            WHERE ward IS NOT NULL
            GROUP BY ward
        ''')
        ward_metrics = []
        for r in ward_rows:
            ward_metrics.append({
                "ward": r['ward'],
                "pending": r['pending_count'],
                "resolved": r['resolved_count'],
                # "quality_score": mock calculation where higher pending means lower score
                "quality_score": max(0, 100 - (r['pending_count'] * 5))
            })
        # Sort wards by quality descending
        ward_metrics.sort(key=lambda x: x['quality_score'], reverse=True)

        # Response performance: percentage of resolved incidents that were resolved under 48 hours
        perf_row = query_db('''
            SELECT 
                COUNT(*) as total_resolved,
                SUM(CASE WHEN (julianday(resolved_at) - julianday(created_at)) * 24 < 48 THEN 1 ELSE 0 END) as fast_resolved
            FROM incidents
            WHERE status = 'resolved' AND resolved_at IS NOT NULL
        ''', one=True)
        
        total_res = perf_row['total_resolved'] or 0
        fast_res = perf_row['fast_resolved'] or 0
        response_performance = round((fast_res / total_res * 100) if total_res > 0 else 100, 1)

        return jsonify({
            'success': True,
            'metrics': {
                'resolution_timeline_hours': avg_resolution_hours,
                'pending_over_60_days': pending_60_days,
                'ward_quality': ward_metrics,
                'response_performance_pct': response_performance
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # Initialize database if needed
    with app.app_context():
        try:
            init_db(app)
            print('✓ Database initialized')
        except Exception as e:
            print(f'Note: {e}')

        # Apply schema additions (idempotent for CREATE TABLE / CREATE VIEW;
        # ALTER TABLE statements will error if columns already exist -- safe to ignore)
        try:
            schema_updates_path = os.path.join('migrations', 'schema_updates.sql')
            if os.path.exists(schema_updates_path):
                with open(schema_updates_path, 'r') as f:
                    updates_sql = f.read()
                db = get_db()
                for statement in updates_sql.split(';'):
                    stmt = statement.strip()
                    if stmt:
                        try:
                            db.execute(stmt)
                        except Exception:
                            pass  # Column/table already exists -- safe to skip
                db.commit()
                print('✓ Schema updates applied')
        except Exception as e:
            print(f'Note (schema_updates): {e}')

        # Start scheduled summary generation (requires apscheduler)
        start_scheduler()
    
    # Run the app
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f'🚀 Starting RoadPulse AI on {host}:{port}')
    app.run(host=host, port=port, debug=debug)
