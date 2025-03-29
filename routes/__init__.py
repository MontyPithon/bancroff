from .auth import setup_auth_routes
from .user import setup_user_routes
from .forms import setup_form_routes
from .approvals import setup_approval_routes

def register_routes(app):
    """Register all application routes"""
    setup_auth_routes(app)
    setup_user_routes(app)
    setup_form_routes(app)
    setup_approval_routes(app)
    
    # Add the index route here since it's simple
    from flask import render_template
    
    @app.route('/')
    def index():
        return render_template('index.html')
