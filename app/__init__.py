"""Flask application factory for RoadPulse AI."""

from flask import Flask
from app.db import close_db, init_db


def create_app():
    """Create and configure the Flask application.
    
    Returns:
        Flask: Configured Flask application instance.
    """
    import os
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
    # Configuration
    app.config['JSON_SORT_KEYS'] = False
    
    # Register database teardown
    app.teardown_appcontext(close_db)
    
    # Register CLI command for database initialization
    @app.cli.command()
    def init_db_command():
        """Initialize the database."""
        init_db(app)
        print('Database initialized.')
    
    # Register blueprints (will be added in app.py)
    
    return app
