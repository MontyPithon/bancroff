from flask import jsonify
from models import User

def setup_api_routes(app):
    """Simple API endpoint for users"""
    
    @app.route('/api/users')
    def api_users():
        """Return all users in a simple format"""
        users = User.query.all()
        user_list = []
        
        for user in users:
            user_list.append({
                'id': user.id,
                'name': user.full_name,
                'email': user.email
            })
        
        return jsonify(user_list) 