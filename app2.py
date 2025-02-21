from flask import Flask, render_template, redirect, url_for, flash, request, session, abort
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import msal
import uuid
import os

# Microsoft Authentication Config
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"
AUTHORITY = "https://login.microsoftonline.com/your-tenant-id"
REDIRECT_PATH = "/getAToken"
SCOPE = ["User.Read"]

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bancroff.db'

# Ensure the database file exists and is accessible
if not os.path.exists('instance'):
    os.makedirs('instance')

with app.app_context():
    db = SQLAlchemy(app)
    db.create_all()

# Database Models
class User(db.Model):
    """User model representing registered users."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column(db.String(255))
    status = db.Column(db.String(20), default='active', nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    provider_user_id = db.Column(db.String(255))
    provider = db.Column(db.String(30))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    role = db.relationship('Role', backref=db.backref('users', lazy=True))

class Role(db.Model):
    """Role model representing different user roles."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)

class Permission(db.Model):
    """Permission model defining specific actions users can perform."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)

class RolePermission(db.Model):
    """Many-to-Many relationship between roles and permissions."""
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), primary_key=True)

class AuditLog(db.Model):
    """Audit log model to track system actions."""
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    user_email = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Permission Check
def has_permission(permission_name):
    """Check if the logged-in user has a specific permission."""
    user_id = session.get("user_id")
    if not user_id:
        flash("Session expired or invalid. Please log in again.", "danger")
        return False

    user = User.query.get(user_id)
    if not user:
        flash("User not found. Contact support.", "danger")
        return False

    result = db.session.execute("""
        SELECT COUNT(*) FROM role_permissions rp
        JOIN permissions p ON rp.permission_id = p.id
        WHERE rp.role_id = :role_id AND p.name = :permission_name
    """, {"role_id": user.role_id, "permission_name": permission_name}).fetchone()
    
    return result[0] > 0

# Decorators for Access Control
def permission_required(permission_name):
    """Decorator to enforce permission-based access control."""
    def decorator(f):
        @wraps(f)
        def wrapped_function(*args, **kwargs):
            if not has_permission(permission_name):
                flash("You do not have the required permission.", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapped_function
    return decorator

# Log Actions
def log_action(action, user_email):
    """Log security and administrative actions with error handling."""
    try:
        new_log = AuditLog(action=action, user_email=user_email)
        db.session.add(new_log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"Error logging action: {e}", "danger")

# Routes
@app.route('/')
def index():
    """Home page route."""
    return render_template('index.html')

@app.route('/users')
@permission_required("view_users")
def user_list():
    """Route to display a list of all users."""
    users = User.query.all()
    return render_template('user_list.html', users=users)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Route to allow new users to register and be assigned a default role."""
    if request.method == "POST":
        email = request.form.get("email").lower()
        full_name = request.form.get("full_name")
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for("login"))
        
        basic_role = Role.query.filter_by(name="BasicUser").first()
        if not basic_role:
            flash("Error: Default role 'BasicUser' not found. Initializing now.", "warning")
            basic_role = Role(name="BasicUser", description="Default user role")
            db.session.add(basic_role)
            db.session.commit()
        
        new_user = User(email=email, full_name=full_name, role=basic_role)
        
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Login route to authenticate users."""
    if request.method == "POST":
        email = request.form.get("email").lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Invalid credentials.", "danger")
            return redirect(url_for("login"))
        session["user_id"] = user.id
        session["role"] = user.role.name
        session["status"] = user.status
        flash("Login successful!", "success")
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Route to handle user logout and clear session."""
    session.clear()
    return redirect(url_for("index"))

# Run Flask Application
if __name__ == '__main__':
    app.run(debug=True, port=50010)
