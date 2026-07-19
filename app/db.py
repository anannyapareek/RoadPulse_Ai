"""Database initialization and connection management for RoadPulse AI."""

import sqlite3
import os
from pathlib import Path


DATABASE_PATH = os.getenv('DATABASE_URL', 'sqlite:///instance/roadpulse.db').replace(
    'sqlite:///', ''
)


def get_db():
    """Get a database connection from the current Flask app context.
    
    Returns:
        sqlite3.Connection: Database connection with row factory for dict-like access.
    """
    from flask import g
    
    if 'db' not in g:
        db_path = DATABASE_PATH
        if not os.path.dirname(db_path):
            db_path = os.path.join('instance', 'roadpulse.db')
        
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    
    return g.db


def close_db(e=None):
    """Close the database connection.
    
    Args:
        e: Optional exception to ignore.
    """
    from flask import g
    
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app=None):
    """Initialize the database with the schema from schema.sql.
    
    Args:
        app: Optional Flask app instance. If not provided, uses current_app.
    """
    if app is None:
        from flask import current_app
        app = current_app
    
    # Ensure instance directory exists
    instance_path = 'instance'
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    # Get schema path
    migrations_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'migrations',
        'schema.sql'
    )
    
    if not os.path.exists(migrations_path):
        raise FileNotFoundError(f"Schema file not found at {migrations_path}")
    
    # Read and execute schema
    with open(migrations_path, 'r') as f:
        schema_sql = f.read()
    
    db = get_db()
    db.executescript(schema_sql)
    db.commit()


def query_db(query, args=(), one=False):
    """Execute a query and return results.
    
    Args:
        query (str): SQL query to execute.
        args (tuple): Query parameters.
        one (bool): If True, return single row; else return all rows.
    
    Returns:
        dict or list: Single row as dict, all rows as list, or None.
    """
    db = get_db()
    cur = db.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=(), commit=True):
    """Execute an insert/update/delete query.
    
    Args:
        query (str): SQL query to execute.
        args (tuple): Query parameters.
        commit (bool): Whether to commit the transaction.
    
    Returns:
        int: Last inserted row ID or rows affected.
    """
    db = get_db()
    cur = db.execute(query, args)
    if commit:
        db.commit()
    result = cur.lastrowid if 'INSERT' in query.upper() else cur.rowcount
    cur.close()
    return result
