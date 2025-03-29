from flask import Flask
import os
import config
from models import db
from routes import register_routes
from utils.data_helpers import initialize_database
from form_schema import rcl_form_schema, withdrawal_form_schema

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure the app from config.py
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['DEBUG'] = config.DEBUG
    
    # Initialize database
    db.init_app(app)
    
    # Create uploads directory if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Register all routes
    register_routes(app)
    
    # Initialize database with required data if it doesn't exist
    with app.app_context():
        if not os.path.exists('./instance/bancroff.db'):
            print("Initializing database...")
            db.create_all()
            initialize_database(rcl_form_schema, withdrawal_form_schema)
            print("Database initialization complete.")
    
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=config.DEBUG, port=config.SERVER_PORT) 