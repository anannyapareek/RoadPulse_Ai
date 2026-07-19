"""Gemini API service for image classification and report generation."""

import requests
import json
import base64
import os
from typing import Dict, Any, Tuple


GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models'


def _read_image_as_base64(image_path: str) -> str:
    """Read an image file and encode it as base64.
    
    Args:
        image_path (str): Path to the image file.
    
    Returns:
        str: Base64-encoded image data.
    
    Raises:
        FileNotFoundError: If image file does not exist.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    return base64.b64encode(image_data).decode('utf-8')


def classify_image(image_path: str, note: str = '') -> Tuple[Dict[str, Any], str]:
    """Classify a road image using Gemini API.
    
    Sends image to Gemini API and extracts incident type, severity, and confidence.
    Uses structured JSON output for consistent parsing.
    
    Args:
        image_path (str): Path to the image file.
        note (str): Optional user note accompanying the image.
    
    Returns:
        Tuple[Dict, str]: Classification result dict and raw response text.
                         Dict contains: incident_type, severity_level, confidence_score, reason
    
    Raises:
        ValueError: If API key is not configured.
        requests.RequestException: If API call fails.
        json.JSONDecodeError: If response cannot be parsed.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured in environment")
    
    # Encode image
    image_base64 = _read_image_as_base64(image_path)
    
    # Determine image type from filename
    if image_path.lower().endswith('.png'):
        media_type = 'image/png'
    elif image_path.lower().endswith('.gif'):
        media_type = 'image/gif'
    elif image_path.lower().endswith('.webp'):
        media_type = 'image/webp'
    else:
        media_type = 'image/jpeg'
    
    # Build Gemini API request
    url = f"{GEMINI_API_URL}/{GEMINI_MODEL}:generateContent"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    prompt = f"""Analyze this road/street image and classify it for road hazard reporting.

User note: {note if note else '(no note provided)'}

Respond with ONLY a valid JSON object (no markdown, no extra text) with these exact fields:
{{
    "incident_type": "one of: pothole, crack, flooding, debris, accident, congestion, other",
    "severity_level": "one of: low, medium, high, critical",
    "confidence_score": 0.0 to 1.0 numeric value,
    "reason": "brief explanation of the classification"
}}

Be strict: if unsure, use confidence < 0.5 and set type to "other"."""
    
    payload = {
        'contents': [
            {
                'parts': [
                    {
                        'text': prompt
                    },
                    {
                        'inlineData': {
                            'mimeType': media_type,
                            'data': image_base64
                        }
                    }
                ]
            }
        ],
        'generationConfig': {
            'responseMimeType': 'application/json'
        }
    }
    
    # Make API call
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        params={'key': GEMINI_API_KEY},
        timeout=30
    )
    
    response.raise_for_status()
    
    # Parse response
    response_json = response.json()
    
    if 'candidates' not in response_json or not response_json['candidates']:
        raise ValueError("No candidates in Gemini response")
    
    candidate = response_json['candidates'][0]
    
    if 'content' not in candidate or not candidate['content'].get('parts'):
        raise ValueError("No content in Gemini candidate")
    
    text_content = candidate['content']['parts'][0].get('text', '{}')
    raw_response = text_content
    
    # Parse the JSON response
    # Newer Gemini models may wrap JSON in markdown fences even with responseMimeType set
    text_to_parse = text_content.strip()
    if text_to_parse.startswith('```'):
        # Strip opening fence (```json or ```)
        lines = text_to_parse.split('\n')
        lines = lines[1:]  # remove first line (```json)
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        text_to_parse = '\n'.join(lines).strip()

    try:
        classification = json.loads(text_to_parse)
    except json.JSONDecodeError:
        # If the response is not valid JSON, create a default response
        classification = {
            'incident_type': 'other',
            'severity_level': 'low',
            'confidence_score': 0.3,
            'reason': 'Could not parse Gemini response'
        }
    
    # Validate required fields
    if 'incident_type' not in classification:
        classification['incident_type'] = 'other'
    if 'severity_level' not in classification:
        classification['severity_level'] = 'low'
    if 'confidence_score' not in classification:
        classification['confidence_score'] = 0.0
    if 'reason' not in classification:
        classification['reason'] = 'No reason provided'
    
    # Ensure confidence_score is a float between 0 and 1
    try:
        confidence = float(classification['confidence_score'])
        classification['confidence_score'] = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        classification['confidence_score'] = 0.0
    
    return classification, raw_response


def generate_report_summary(
    incident_type: str,
    severity_level: str,
    confidence_score: float,
    location_address: str = 'Unknown location',
    device_id: str = 'Unknown device',
    note: str = ''
) -> str:
    """Generate a human-readable report summary using Gemini.
    
    Args:
        incident_type (str): Type of incident (e.g., 'pothole').
        severity_level (str): Severity level (e.g., 'high').
        confidence_score (float): Confidence score between 0 and 1.
        location_address (str): Address or location description.
        device_id (str): Reporting device ID.
        note (str): User note.
    
    Returns:
        str: Generated summary text.
    
    Raises:
        ValueError: If API key is not configured.
        requests.RequestException: If API call fails.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured in environment")
    
    url = f"{GEMINI_API_URL}/{GEMINI_MODEL}:generateContent"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    prompt = f"""Generate a brief, professional incident report summary (2-3 sentences max).

Incident Details:
- Type: {incident_type}
- Severity: {severity_level}
- Confidence: {confidence_score:.1%}
- Location: {location_address}
- Device: {device_id}
- User note: {note if note else '(none)'}

Provide ONLY the summary text, no JSON or formatting."""
    
    payload = {
        'contents': [
            {
                'parts': [
                    {
                        'text': prompt
                    }
                ]
            }
        ]
    }
    
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        params={'key': GEMINI_API_KEY},
        timeout=15
    )
    
    response.raise_for_status()
    
    response_json = response.json()
    
    if 'candidates' not in response_json or not response_json['candidates']:
        return "Unable to generate summary at this time."
    
    candidate = response_json['candidates'][0]
    
    if 'content' not in candidate or not candidate['content'].get('parts'):
        return "Unable to generate summary at this time."
    
    summary = candidate['content']['parts'][0].get('text', '').strip()
    
    return summary if summary else "Summary generation incomplete."
