"""Incident routing rules for department assignment."""


DEPARTMENT_MAP = {
    'pothole': {
        'department': 'Public Works',
        'priority': 'high',
        'response_time_hours': 24,
        'description': 'Road surface damage requiring fill/repair'
    },
    'crack': {
        'department': 'Public Works',
        'priority': 'medium',
        'response_time_hours': 48,
        'description': 'Pavement cracking or surface deterioration'
    },
    'flooding': {
        'department': 'Drainage/Stormwater',
        'priority': 'critical',
        'response_time_hours': 4,
        'description': 'Water pooling or flooding on road surface'
    },
    'debris': {
        'department': 'Public Works',
        'priority': 'medium',
        'response_time_hours': 2,
        'description': 'Debris on road requiring removal'
    },
    'accident': {
        'department': 'Emergency Services',
        'priority': 'critical',
        'response_time_hours': 0,
        'description': 'Vehicle collision or traffic incident'
    },
    'congestion': {
        'department': 'Traffic Management',
        'priority': 'low',
        'response_time_hours': 1,
        'description': 'Unusual traffic congestion pattern'
    },
    'other': {
        'department': 'General Services',
        'priority': 'low',
        'response_time_hours': 48,
        'description': 'Other road or traffic issue'
    }
}


def get_routing_rule(incident_type: str) -> dict:
    """Get the routing rule for an incident type.
    
    Args:
        incident_type (str): Type of incident.
    
    Returns:
        dict: Routing rule with department, priority, response_time_hours, description.
    """
    return DEPARTMENT_MAP.get(incident_type.lower(), DEPARTMENT_MAP['other'])


def get_department(incident_type: str) -> str:
    """Get the assigned department for an incident type.
    
    Args:
        incident_type (str): Type of incident.
    
    Returns:
        str: Department name.
    """
    return get_routing_rule(incident_type)['department']


def get_priority(incident_type: str) -> str:
    """Get the priority level for an incident type.
    
    Args:
        incident_type (str): Type of incident.
    
    Returns:
        str: Priority level (low, medium, high, critical).
    """
    return get_routing_rule(incident_type)['priority']


def get_response_time_hours(incident_type: str) -> int:
    """Get the expected response time in hours.
    
    Args:
        incident_type (str): Type of incident.
    
    Returns:
        int: Response time in hours.
    """
    return get_routing_rule(incident_type)['response_time_hours']
