from flask import Flask, jsonify, request
import os
import config
from models import db
from routes import register_routes
from utils.data_helpers import initialize_database
from form_schema import rcl_form_schema, withdrawal_form_schema
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure the app from config.py
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['DEBUG'] = config.DEBUG
    
    # Session configuration
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Initialize CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Initialize database
    db.init_app(app)
    
    # Create uploads directory if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Register all routes
    register_routes(app)
    
    # Add CORS headers to API responses
    @app.after_request
    def add_cors_headers(response):
        if request.path.startswith('/api/'):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET'
        return response
    
    # Initialize database with required data if it doesn't exist
    with app.app_context():
        db_path = '/app/instance/bancroff.db'
        if not os.path.exists(db_path):
            print("Initializing database...")
            db.create_all()
            initialize_database(rcl_form_schema, withdrawal_form_schema)
            print("Database initialization complete.")
    
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # When running in Docker, bind to 0.0.0.0 to be accessible
    host = '0.0.0.0'
    app.run(debug=config.DEBUG, host=host, port=config.SERVER_PORT) 