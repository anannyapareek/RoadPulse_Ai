"""General utility functions for RoadPulse AI."""

import os
import uuid
import mimetypes
from typing import Tuple
from datetime import datetime


def generate_device_id() -> str:
    """Generate a unique device ID for anonymous mobile devices.
    
    Returns:
        str: Unique device ID (UUID4 format).
    """
    return str(uuid.uuid4())


def validate_device_id(device_id: str) -> bool:
    """Validate that a device ID is in the correct format.
    
    Args:
        device_id (str): Device ID to validate.
    
    Returns:
        bool: True if valid format, False otherwise.
    """
    if not device_id or not isinstance(device_id, str):
        return False
    
    # Allow alphanumeric, hyphens, underscores
    return all(c.isalnum() or c in '-_' for c in device_id) and len(device_id) > 0


def save_uploaded_image(file_obj, upload_folder: str = 'uploads') -> Tuple[str, str]:
    """Save an uploaded image file and return filename and path.
    
    Args:
        file_obj: File object from Flask request.files.
        upload_folder (str): Directory to save files.
    
    Returns:
        Tuple[str, str]: (filename, full_path).
    
    Raises:
        ValueError: If file is invalid or upload fails.
    """
    if not file_obj or file_obj.filename == '':
        raise ValueError("No file provided")
    
    # Validate file extension
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    filename = file_obj.filename
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise ValueError(f"File type not allowed: {file_ext}")
    
    # Create upload folder if needed
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_name = f"incident_{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"
    
    file_path = os.path.join(upload_folder, unique_name)
    
    # Save file
    try:
        file_obj.save(file_path)
    except Exception as e:
        raise ValueError(f"Failed to save file: {str(e)}")
    
    return unique_name, file_path


def get_mime_type(filename: str) -> str:
    """Get MIME type for a file.
    
    Args:
        filename (str): Filename or file extension.
    
    Returns:
        str: MIME type (default 'application/octet-stream').
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'


def format_timestamp(timestamp: str, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Format a timestamp string for display.
    
    Args:
        timestamp (str): Timestamp string from database.
        format_str (str): Output format string.
    
    Returns:
        str: Formatted timestamp.
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime(format_str)
    except Exception:
        return timestamp


def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate a string to max length, adding ellipsis if needed.
    
    Args:
        text (str): Text to truncate.
        max_length (int): Maximum length.
    
    Returns:
        str: Truncated text.
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + '...'
