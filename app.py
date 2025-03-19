from flask import Flask, render_template, redirect, url_for, flash, request, session, render_template_string
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email
import msal
import uuid
from flask_sqlalchemy import SQLAlchemy
from faker import Faker
from functools import wraps
import os
    

CLIENT_ID = "1daa4a2e-7a38-4225-854c-45d232e9ccbf"              # Replace with your Application (client) IDimport uuid
CLIENT_SECRET = "zjo8Q~N4HOF61PaaHwEOVGwLMFH6vondPFxWPcjN"      # Replace with your Client Secret
AUTHORITY = "https://login.microsoftonline.com/170bbabd-a2f0-4c90-ad4b-0e8f0f0c4259"  # Replace with your Tenant ID
REDIRECT_PATH = "/getAToken"  # Must match the registered redirect URI
SCOPE = ["User.Read"]  # Adjust scopes as needed for your app

# Initialize the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'password'  # Secret key for session management


# Enable debug mode for detailed error messages
app.debug = True

# init database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bancroff.db'
db = SQLAlchemy(app)

#db models
#TODO: possibly remove provider_user_id and provider and add in future if needed
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column(db.String(255))
    status = db.Column(db.String(20), default='active', nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    provider_user_id = db.Column(db.String(255))
    provider = db.Column(db.String(30))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    role = db.relationship('Role', backref=db.backref('users', lazy=True))
    signature_path = db.Column(db.String(255))

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)

class RolePermission(db.Model):
    __tablename__ = 'role_permissions'
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), primary_key=True)

# Define the UserForm for creating and updating users
class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])  # Name field, required
    email = StringField('Email', validators=[DataRequired(), Email()])  # Email field, required and must be a valid email
    role = SelectField('Role', choices=[('basic_user', 'Basic User'), ('admin', 'Administrator')])  # Role selection
    status = SelectField('Status', choices=[('active', 'Active'), ('deactivated', 'Deactivated')])  # Status selection
    submit = SubmitField('Submit')  # Submit button

def add_fake_data(num_users=5):
    fake = Faker()
    try:
        roles = [
            Role(name='admin', description='Administrator role with full permissions'),
            Role(name='basic_user', description='Regular user role with limited permissions')
        ]
        db.session.add_all(roles)
        db.session.commit()

        permissions = [
            Permission(name='read', description='Read permission'),
            Permission(name='write', description='Write permission'),
            Permission(name='delete', description='Delete permission')
        ]
        db.session.add_all(permissions)
        db.session.commit()
        
        role_permissions = [
            RolePermission(role_id=1, permission_id=1),
            RolePermission(role_id=1, permission_id=2),
            RolePermission(role_id=1, permission_id=3),
            RolePermission(role_id=2, permission_id=1)
        ]
        db.session.add_all(role_permissions)
        db.session.commit()

        for _ in range(num_users):
            fake_user = User(
                email=fake.email(),
                full_name=fake.name(),
                status=fake.random_element(['active', 'deactivated']),
                provider_user_id=fake.uuid4(),
                provider=fake.random_element(['Google', 'Microsoft', 'Yahoo', 'Apple']),
                role_id=2
            )
            db.session.add(fake_user)
        
        db.session.commit()
        print("Fake data added successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.session.rollback()

# create database with fake data
if not os.path.exists('./instance/bancroff.db'):
    with app.app_context():
        print('test')
        db.create_all()
        add_fake_data()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

def active_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("status") == "deactivated":
            flash("Your account is deactivated. Please contact the administrator.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

# Route for the home page
@app.route('/')
def index():
    print(session) 
    return render_template('index.html')

# Route for displaying the list of users
@app.route('/users')
@admin_required
@active_required
def user_list():
    if not session.get("user"):
        return redirect(url_for("login"))
    users = User.query.all()
    return render_template('user_list.html', users=users)

# Route for creating a new user
@app.route('/create_user', methods=['GET', 'POST'])
@admin_required
@active_required
def create_user():
    if not session.get("user"):
        return redirect(url_for("login"))
    form = UserForm()
    if form.validate_on_submit():
        try:
            selected_role = Role.query.filter_by(name=form.role.data).first()
            new_user = User(
                email=form.email.data,
                full_name=form.name.data,
                status=form.status.data,
                provider_user_id=None,
                provider=None,
                role=selected_role
            )
            db.session.add(new_user)
            db.session.commit()
            flash('User created successfully!', 'success')
            return redirect(url_for('user_list'))
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
    return render_template('create_user.html', form=form)
# Route for updating an existing user
@app.route('/update_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
@active_required
def update_user(user_id):
    if not session.get("user"):
        return redirect(url_for("login"))
    form = UserForm()
    user = User.query.get(user_id)
    
    if user:
        if form.validate_on_submit():
            try:
                user.full_name = form.name.data
                user.email = form.email.data
                user.role = Role.query.filter_by(name=form.role.data).first()
                user.status = form.status.data
                db.session.commit()
                flash('User updated successfully!', 'success')
                return redirect(url_for('user_list'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'danger')
        else:
            form.name.data = user.full_name
            form.email.data = user.email
            form.role.data = user.role.name
            form.status.data = user.status
    else:
        flash('User not found!', 'danger')
        return redirect(url_for('user_list'))
    return render_template('update_user.html', form=form, user=user)

# Route for deleting a user
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@admin_required
@active_required
def delete_user(user_id):
    if not session.get("user"):
        return redirect(url_for("login"))
    try:
        user = User.query.get(user_id)
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
    return redirect(url_for('user_list'))

# Route for deactivating a user
@app.route('/deactivate_user/<int:user_id>', methods=['POST'])
@admin_required
@active_required
def deactivate_user(user_id):
    if not session.get("user"):
        return redirect(url_for("login"))
    try:
        user = User.query.get(user_id)
        if user:
            user.status = 'deactivated'
            db.session.commit()
            flash('User deactivated successfully!', 'success')
        else:
            flash('User not found!', 'danger')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
    return redirect(url_for('user_list'))

# Route for reactivating a user
@app.route('/reactivate_user/<int:user_id>', methods=['POST'])
@admin_required
@active_required
def reactivate_user(user_id):
    if not session.get("user"):
        return redirect(url_for("login"))
    try:
        user = User.query.get(user_id)
        if user:
            user.status = 'active'
            db.session.commit()
            flash('User reactivated successfully!', 'success')
        else:
            flash('User not found!', 'danger')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
    return redirect(url_for('user_list'))

@app.route("/login")  # Login Route – Render Login Page
def login():
    return render_template('login.html')

@app.route("/start_login")  # Start Login Route – Redirect to Microsoft Login
def start_login():
    session["state"] = str(uuid.uuid4())
    auth_url = _build_auth_url(session["state"])
    return redirect(auth_url)

def _build_auth_url(state):  # Build the Authorization URL:
    msal_app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPE,
        state=state,
        redirect_uri=url_for("authorized", _external=True)
    )
    return auth_url

@app.route(REDIRECT_PATH)  # Callback (Authorized) Route – Process the Token
def authorized():
    # Verify state to mitigate CSRF attacks
    if request.args.get("state") != session.get("state"):
        return redirect(url_for("index"))

    # Handle any error returned in the query parameters
    if "error" in request.args:
        return f"Authentication error: {request.args.get('error')}"

    # Process the authorization code
    if "code" in request.args:
        code = request.args.get("code")
        msal_app = msal.ConfidentialClientApplication(
            CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
        )
        result = msal_app.acquire_token_by_authorization_code(
            code,
            scopes=SCOPE,
            redirect_uri=url_for("authorized", _external=True)
        )
        if "error" in result:
            return f"Error: {result.get('error')}"
        # Store user information in the session (e.g., user claims from the ID token)
        session["user"] = result.get("id_token_claims")

        # Add user to database if not already present
        user_info = session["user"]
        user = User.query.filter_by(email=user_info["preferred_username"].lower()).first()
        if not user:
            admin_user_role = Role.query.filter_by(name='admin').first()
            new_user = User(
                email=user_info["preferred_username"].lower(),
                full_name=user_info["name"],
                provider_user_id=user_info["oid"],
                provider="Microsoft",
                role=admin_user_role
            )
            db.session.add(new_user)
            db.session.commit()
            session["role"] = "admin" #default everyone admin
            session["status"] = "active"
        else:
            session["role"] = user.role.name
            session["status"] = user.status

        return redirect(url_for("index"))
    
    return redirect(url_for("index"))

@app.route("/logout")  # Logout Route – Clear the User Session
def logout():
    session.clear()
    return redirect(url_for("index"))

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads') #3/18 Configure the folder where uploaded signature images will be stored
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'} #3/18 Define a set of allowed file extensions for uploaded images

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
@app.route('/upload_signature', methods=['GET', 'POST']) # Define a route to handle the signature upload
def upload_signature():
    if request.method == 'POST':
        # Check if the POST request has the file part
        if 'signature' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['signature']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # TODO: Save file_path in your database for the user
            flash('Signature uploaded successfully!')
            return redirect(url_for('upload_signature'))
    # Minimal form template
    return render_template_string('''
        <!doctype html>
        <title>Upload Signature</title>
        <h1>Upload your Signature</h1>
        <form method="post" enctype="multipart/form-data">
          <input type="file" name="signature">
          <input type="submit" value="Upload">
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul>
            {% for message in messages %}
              <li>{{ message }}</li>
            {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
    ''')
# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True, port=50010)
