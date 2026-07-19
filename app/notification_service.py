"""Notification service for dispatch alerts via SMS and voice calls."""

from datetime import datetime
from app.db import query_db, execute_db
from app.dispatch_audit import log_dispatch_action


def send_dispatch_call(phone, officer_name, incident_details):
    """Queue a voice call notification for dispatch.
    
    Args:
        phone (str): Officer phone number.
        officer_name (str): Officer name.
        incident_details (dict): Incident info (type, location, severity, etc.).
    
    Returns:
        dict: Notification details or error dict.
    """
    try:
        # Construct message for voice call
        message = f"Dispatch alert for {officer_name}. "
        message += f"Incident type: {incident_details.get('incident_type', 'unknown')}. "
        message += f"Location: {incident_details.get('location_desc', 'coordinates provided')}. "
        message += f"Severity: {incident_details.get('severity_level', 'unknown')}."
        
        notification_id = execute_db(
            '''INSERT INTO notification_queue 
               (officer_assignment_id, notification_type, phone_number, message_body, status)
               VALUES (?, 'voice_call', ?, ?, 'pending')''',
            (incident_details.get('assignment_id'), phone, message)
        )
        
        return {
            'success': True,
            'notification_id': notification_id,
            'type': 'voice_call',
            'phone': phone,
            'message': message
        }
    except Exception as e:
        return {'error': str(e)}


def send_dispatch_sms(phone, summary):
    """Queue an SMS notification for dispatch.
    
    Args:
        phone (str): Officer phone number.
        summary (str): SMS message summary (brief, under 160 chars).
    
    Returns:
        dict: Notification details or error dict.
    """
    try:
        notification_id = execute_db(
            '''INSERT INTO notification_queue 
               (officer_assignment_id, notification_type, phone_number, message_body, status)
               VALUES (?, 'sms', ?, ?, 'pending')''',
            (None, phone, summary)
        )
        
        return {
            'success': True,
            'notification_id': notification_id,
            'type': 'sms',
            'phone': phone,
            'message': summary
        }
    except Exception as e:
        return {'error': str(e)}


def queue_notification(officer_assignment_id, notification_type, phone_number=None, 
                      message_body=None):
    """Add a notification to the queue for processing.
    
    Args:
        officer_assignment_id (int): Assignment ID.
        notification_type (str): 'sms' or 'voice_call'.
        phone_number (str): Phone to notify.
        message_body (str): Message content.
    
    Returns:
        dict: Notification queue entry or error dict.
    """
    try:
        if not phone_number or not message_body:
            return {'error': 'Phone number and message body are required'}
        
        notification_id = execute_db(
            '''INSERT INTO notification_queue 
               (officer_assignment_id, notification_type, phone_number, message_body, status)
               VALUES (?, ?, ?, ?, 'pending')''',
            (officer_assignment_id, notification_type, phone_number, message_body)
        )
        
        return {
            'success': True,
            'notification_id': notification_id,
            'assignment_id': officer_assignment_id,
            'type': notification_type,
            'status': 'queued'
        }
    except Exception as e:
        return {'error': str(e)}


def process_notification_queue():
    """Process pending notifications in the queue.
    
    This function should be called periodically (e.g., every 2 minutes) by a scheduler.
    It attempts to send all pending notifications and updates their status.
    
    Returns:
        dict: Processing summary with counts of processed, sent, and failed notifications.
    """
    try:
        # Get all pending notifications
        pending = query_db(
            '''SELECT nq.*, oa.officer_id, i.incident_id
               FROM notification_queue nq
               JOIN officer_assignments oa ON nq.officer_assignment_id = oa.id
               JOIN incidents i ON oa.incident_id = i.id
               WHERE nq.status = 'pending' AND nq.retry_count < nq.max_retries
               ORDER BY nq.created_at ASC
               LIMIT 100'''
        )
        
        sent_count = 0
        failed_count = 0
        
        for notification in pending:
            result = _send_notification(notification)
            
            if result.get('success'):
                # Mark as sent
                execute_db(
                    '''UPDATE notification_queue 
                       SET status = 'sent', sent_at = CURRENT_TIMESTAMP
                       WHERE id = ?''',
                    (notification['id'],)
                )
                sent_count += 1
            else:
                # Increment retry count
                execute_db(
                    '''UPDATE notification_queue 
                       SET retry_count = retry_count + 1
                       WHERE id = ?''',
                    (notification['id'],)
                )
                
                # Check if max retries exceeded
                new_retry_count = notification['retry_count'] + 1
                if new_retry_count >= notification['max_retries']:
                    execute_db(
                        '''UPDATE notification_queue 
                           SET status = 'failed', failed_at = CURRENT_TIMESTAMP
                           WHERE id = ?''',
                        (notification['id'],)
                    )
                    failed_count += 1
        
        return {
            'success': True,
            'processed': len(pending),
            'sent': sent_count,
            'failed': failed_count,
            'retried': len(pending) - sent_count - failed_count
        }
    except Exception as e:
        return {'error': str(e)}


def _send_notification(notification):
    """Internal function to send a single notification via Twilio or email.
    
    Args:
        notification (dict): Notification record from database.
    
    Returns:
        dict: Result with 'success' boolean and optional 'twilio_sid'.
    """
    try:
        # In production, this would use Twilio SDK
        # For now, we'll simulate successful sending
        phone = notification['phone_number']
        msg_type = notification['notification_type']
        message = notification['message_body']
        
        # Placeholder for Twilio integration
        # In real implementation, you would do:
        # if msg_type == 'sms':
        #     response = twilio_client.messages.create(to=phone, from_=TWILIO_PHONE, body=message)
        # else:
        #     response = twilio_client.calls.create(to=phone, from_=TWILIO_PHONE, url=twiml_url)
        
        # For now, simulate success
        twilio_sid = f"SM_{notification['id']}_{datetime.utcnow().timestamp()}"
        
        return {
            'success': True,
            'twilio_sid': twilio_sid,
            'notification_id': notification['id']
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def handle_notification_callback(twilio_sid, status):
    """Handle Twilio webhook callback for message delivery status.
    
    Args:
        twilio_sid (str): Twilio message/call SID.
        status (str): Delivery status ('delivered', 'failed', 'undelivered', etc.).
    
    Returns:
        dict: Status update result or error dict.
    """
    try:
        # Find notification by Twilio SID
        notification = query_db(
            'SELECT * FROM notification_queue WHERE twilio_sid = ?',
            (twilio_sid,),
            one=True
        )
        
        if not notification:
            return {'error': 'Notification not found'}
        
        # Map Twilio status to our status
        status_map = {
            'delivered': 'sent',
            'sent': 'sent',
            'failed': 'failed',
            'undelivered': 'failed',
            'queued': 'pending'
        }
        
        new_status = status_map.get(status, 'pending')
        
        execute_db(
            'UPDATE notification_queue SET status = ? WHERE id = ?',
            (new_status, notification['id'])
        )
        
        return {
            'success': True,
            'notification_id': notification['id'],
            'status': new_status
        }
    except Exception as e:
        return {'error': str(e)}


def retry_failed_notifications():
    """Retry sending failed notifications that haven't exceeded max retries.
    
    Returns:
        dict: Retry summary with counts.
    """
    try:
        failed = query_db(
            '''SELECT * FROM notification_queue 
               WHERE status = 'failed' AND retry_count < max_retries
               ORDER BY created_at ASC
               LIMIT 50'''
        )
        
        reset_count = 0
        for notification in failed:
            # Reset to pending for retry
            execute_db(
                '''UPDATE notification_queue 
                   SET status = 'pending', retry_count = 0
                   WHERE id = ?''',
                (notification['id'],)
            )
            reset_count += 1
        
        return {
            'success': True,
            'retried': reset_count
        }
    except Exception as e:
        return {'error': str(e)}
