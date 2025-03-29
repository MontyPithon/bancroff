from flask import Flask, render_template, redirect, url_for, flash, request, session, render_template_string, jsonify
import json
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
from form_schema import rcl_form_schema, withdrawal_form_schema


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

class RequestType(db.Model):
    __tablename__ = 'request_types'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    form_schema = db.Column(db.JSON, nullable=True)
    template_doc_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    requests = db.relationship('Request', backref='request_type', lazy=True)
    workflows = db.relationship('ApprovalWorkflow', backref='request_type', lazy=True)

class Request(db.Model):
    __tablename__ = 'requests'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type_id = db.Column(db.Integer, db.ForeignKey('request_types.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    form_data = db.Column(db.JSON)
    status = db.Column(db.String(50), default='draft')
    final_document_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())
    requester = db.relationship('User', backref='requests')
    approvals = db.relationship('RequestApproval', backref='request', lazy=True)

class UserSignature(db.Model):
    __tablename__ = 'user_signatures'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    signature_image_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False)
    user = db.relationship('User', backref='signatures')

class ApprovalWorkflow(db.Model):
    __tablename__ = 'approval_workflows'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_type_id = db.Column(db.Integer, db.ForeignKey('request_types.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    steps = db.relationship('ApprovalStep', backref='workflow', lazy=True, order_by='ApprovalStep.step_order')

class ApprovalStep(db.Model):
    __tablename__ = 'approval_steps'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('approval_workflows.id'), nullable=False)
    step_order = db.Column(db.Integer, nullable=False)
    approver_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    approver_role = db.relationship('Role')
    approvals = db.relationship('RequestApproval', backref='step', lazy=True)

class RequestApproval(db.Model):
    __tablename__ = 'request_approvals'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey('approval_steps.id'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(50), default='pending')
    comments = db.Column(db.Text)
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    approver = db.relationship('User', backref='approvals')

# Define the UserForm for creating and updating users
class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])  # Name field, required
    email = StringField('Email', validators=[DataRequired(), Email()])  # Email field, required and must be a valid email
    role = SelectField('Role', choices=[
        ('basic_user', 'Basic User'),
        ('admin', 'Administrator'),
        ('dean', 'Dean'),
        ('advisor', 'Advisor'),
        ('chair', 'Chair')
    ])
    status = SelectField('Status', choices=[('active', 'Active'), ('deactivated', 'Deactivated')])  # Status selection
    submit = SubmitField('Submit')  # Submit button

# Add this function to initialize RCL-related data in the database
def add_rcl_data():
    """Add RCL (Reduced Course Load) related data to the database"""
    try:
        # Create RCL request type if it doesn't exist
        rcl_type = RequestType.query.filter_by(name='RCL').first()
        if not rcl_type:
            rcl_type = RequestType(
                name='RCL',
                description='Reduced Course Load request for graduate students',
                form_schema=rcl_form_schema,
                template_doc_path=None  # Path to template document if needed
            )
            db.session.add(rcl_type)
            db.session.commit()
            print("RCL request type added")
        
        # Create necessary roles for approval workflow if they don't exist
        advisor_role = Role.query.filter_by(name='advisor').first()
        if not advisor_role:
            advisor_role = Role(
                name='advisor',
                description='Academic Advisor role'
            )
            db.session.add(advisor_role)
        
        chair_role = Role.query.filter_by(name='chair').first()
        if not chair_role:
            chair_role = Role(
                name='chair',
                description='Department Chair role'
            )
            db.session.add(chair_role)
        
        dean_role = Role.query.filter_by(name='dean').first()
        if not dean_role:
            dean_role = Role(
                name='dean',
                description='College Dean role'
            )
            db.session.add(dean_role)
        
        db.session.commit()
        print("RCL roles added")
        
        # Create approval workflow for RCL requests if it doesn't exist
        workflow = ApprovalWorkflow.query.filter_by(
            request_type_id=rcl_type.id, 
            name='RCL Approval'
        ).first()
        
        if not workflow:
            workflow = ApprovalWorkflow(
                request_type_id=rcl_type.id,
                name='RCL Approval',
                description='Approval workflow for Reduced Course Load requests'
            )
            db.session.add(workflow)
            db.session.commit()
            
            # Create approval steps
            steps = [
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=1,
                    approver_role_id=advisor_role.id,
                    name='Academic Advisor Approval'
                ),
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=2,
                    approver_role_id=chair_role.id,
                    name='Department Chair Approval'
                ),
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=3,
                    approver_role_id=dean_role.id,
                    name='College Dean Approval'
                )
            ]
            db.session.add_all(steps)
            db.session.commit()
            print("RCL approval workflow and steps added")
        
    except Exception as e:
        print(f"An error occurred while adding RCL data: {e}")
        db.session.rollback()

def add_withdrawal_form_data():
    """Add Withdrawal form related data to the database"""
    try:
        # Create Withdrawal request type if it doesn't exist
        withdrawal_type = RequestType.query.filter_by(name='Withdrawal').first()
        if not withdrawal_type:
            withdrawal_type = RequestType(
                name='Withdrawal',
                description='Medical/Administrative Term Withdrawal request',
                form_schema=withdrawal_form_schema,
                template_doc_path=None  # Path to template document if needed
            )
            db.session.add(withdrawal_type)
            db.session.commit()
            print("Withdrawal request type added")
        
        # Get or create necessary roles for approval workflow
        advisor_role = Role.query.filter_by(name='advisor').first()
        if not advisor_role:
            advisor_role = Role(
                name='advisor',
                description='Academic Advisor role'
            )
            db.session.add(advisor_role)
        
        chair_role = Role.query.filter_by(name='chair').first()
        if not chair_role:
            chair_role = Role(
                name='chair',
                description='Department Chair role'
            )
            db.session.add(chair_role)
        
        dean_role = Role.query.filter_by(name='dean').first()
        if not dean_role:
            dean_role = Role(
                name='dean',
                description='College Dean role'
            )
            db.session.add(dean_role)
        
        # Remove health_role creation since we're eliminating that step
        
        db.session.commit()
        print("Withdrawal roles added/confirmed")
        
        # Create approval workflow for Withdrawal requests if it doesn't exist
        workflow = ApprovalWorkflow.query.filter_by(
            request_type_id=withdrawal_type.id, 
            name='Withdrawal Approval'
        ).first()
        
        if not workflow:
            workflow = ApprovalWorkflow(
                request_type_id=withdrawal_type.id,
                name='Withdrawal Approval',
                description='Approval workflow for Medical/Administrative Term Withdrawal requests'
            )
            db.session.add(workflow)
            db.session.commit()
            
            # Create approval steps - same process for both withdrawal types
            steps = [
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=1,
                    approver_role_id=advisor_role.id,
                    name='Academic Advisor Approval'
                ),
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=2,
                    approver_role_id=chair_role.id,
                    name='Department Chair Approval'
                ),
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=3,
                    approver_role_id=dean_role.id,
                    name='College Dean Final Approval'
                )
            ]
            db.session.add_all(steps)
            db.session.commit()
            print("Withdrawal approval workflow and steps added")
        
    except Exception as e:
        print(f"An error occurred while adding Withdrawal form data: {e}")
        db.session.rollback()

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
        add_rcl_data()
        add_withdrawal_form_data()

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
    
@app.route('/upload_signature', methods=['GET', 'POST'])
def upload_signature():
    if request.method == 'POST':
        # Check if the file part is present in the request
        if 'signature' not in request.files:
            flash('No file part in the request')
            return redirect(request.url)
        
        file = request.files['signature']
        
        # Check if a file was selected
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        # Validate and save the file
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            flash('Signature uploaded successfully')
            return redirect(url_for('success'))  # Define a 'success' route or page as needed

    # Render the upload form (GET request)
    return render_template('upload_signature.html')

@app.route('/rcl_form', methods=['GET', 'POST'])
@active_required
def rcl_form():
    print(session)
    print(session.get("user"))
    if not session.get("user"):
        return redirect(url_for("login"))
    
    if request.method == 'POST':
        try:
            user_email = session['user'].get('preferred_username').lower()
            current_user = User.query.filter_by(email=user_email).first()

            rcl_type = RequestType.query.filter_by(name='RCL').first()
            if not rcl_type:
                flash('RCL form type not found in the database', 'danger')
                return redirect(url_for('index'))            
            if not current_user:
                flash('User not found. Please log in again.', 'danger')
                return redirect(url_for('login'))
            
            # process form data 
            form_data = {}
            form_data['iai'] = request.form.getlist('iai[]')
            form_data['reason'] = request.form.get('reason')
            form_data['letter_attached'] = 'letter_attached' in request.form
            form_data['track'] = request.form.get('track')

            if form_data['track'] == 'non_thesis':
                form_data['non_thesis_hours'] = request.form.get('non_thesis_hours')
            elif form_data['track'] == 'thesis':
                form_data['thesis_hours'] = request.form.get('thesis_hours')

            form_data['semester'] = request.form.get('semester')
            if form_data['semester'] == 'fall':
                form_data['year'] = '20' + request.form.get('fall_year', '')
            elif form_data['semester'] == 'spring':
                form_data['year'] = '20' + request.form.get('spring_year', '')
            
            # max 4 drops
            form_data['courses'] = []
            for i in range(1, 4):
                course = request.form.get(f'course{i}')
                if course:
                    form_data['courses'].append(course)

            form_data['remaining_hours'] = request.form.get('remaining_hours')
            form_data['ps_id'] = request.form.get('ps_id')
    
            from datetime import date
            form_data['signature_date'] = str(date.today())

            # create request
            semester_info = f"{form_data['semester']} {form_data['year']}"
            new_request = Request(
                type_id=rcl_type.id,
                requester_id=current_user.id,
                title=f"RCL Request - {semester_info}",
                form_data=form_data,
                status='submitted' 
            )
            db.session.add(new_request)
            db.session.commit()
            
            # create entries in approval table set as pending
            workflow = ApprovalWorkflow.query.filter_by(request_type_id=rcl_type.id).first()
            if workflow:
                for step in workflow.steps:
                    approval = RequestApproval(
                        request_id=new_request.id,
                        step_id=step.id,
                        status='pending'
                    )
                    db.session.add(approval)
                db.session.commit()
                flash('RCL Form submitted successfully and sent for approval!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while submitting the RCL form: {str(e)}', 'danger')
            return redirect(url_for('rcl_form'))
    
    # GET request
    return render_template('rcl_form.html')

@app.route('/withdrawal_form', methods=['GET', 'POST'])
@active_required
def withdrawal_form():
    if not session.get("user"):
        return redirect(url_for("login"))
    
    if request.method == 'POST':
        try:
            user_email = session['user'].get('preferred_username').lower()
            current_user = User.query.filter_by(email=user_email).first()

            withdrawal_type = RequestType.query.filter_by(name='Withdrawal').first()
            if not withdrawal_type:
                flash('Withdrawal form type not found in the database', 'danger')
                return redirect(url_for('index'))
            if not current_user:
                flash('User not found. Please log in again.', 'danger')
                return redirect(url_for('login'))
            

            form_data = {}
            form_data['myUHID'] = request.form.get('myUHID')
            form_data['college'] = request.form.get('college')
            form_data['planDegree'] = request.form.get('planDegree')
            form_data['address'] = request.form.get('address')
            form_data['phoneNumber'] = request.form.get('phoneNumber')
            form_data['termYear'] = request.form.get('termYear')
            form_data['reason'] = request.form.get('reason')
            form_data['lastDateAttended'] = request.form.get('lastDateAttended')
            form_data['financialAssistance'] = request.form.get('financialAssistance') == 'yes'
            form_data['studentHealthInsurance'] = request.form.get('studentHealthInsurance') == 'yes'
            form_data['campusHousing'] = request.form.get('campusHousing') == 'yes'
            form_data['visaStatus'] = request.form.get('visaStatus') == 'yes'
            form_data['giBillBenefits'] = request.form.get('giBillBenefits') == 'yes'
            form_data['withdrawalType'] = request.form.get('withdrawalType')
            form_data['coursesToWithdraw'] = request.form.get('coursesToWithdraw')
            form_data['additionalComments'] = request.form.get('additionalComments')
            
            from datetime import date
            form_data['submissionDate'] = str(date.today())
                
            # create request
            new_request = Request(
                type_id=withdrawal_type.id,
                requester_id=current_user.id,
                title=f"Withdrawal Request - {form_data['termYear']}",
                form_data=form_data,
                status='submitted'
            )
            db.session.add(new_request)
            db.session.commit()
            
            # create entries in approval table set as pending
            workflow = ApprovalWorkflow.query.filter_by(request_type_id=withdrawal_type.id).first()
            if workflow:
                for step in workflow.steps:
                    approval = RequestApproval(
                        request_id=new_request.id,
                        step_id=step.id,
                        status='pending'
                    )
                    db.session.add(approval)
                
                db.session.commit()
                flash('Withdrawal Form submitted successfully and sent for approval!', 'success')
            return redirect(url_for('my_requests'))
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR processing withdrawal form: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'An error occurred while submitting the withdrawal form: {str(e)}', 'danger')
            return redirect(url_for('withdrawal_form'))
    
    # GET request
    return render_template('withdraw_form.html')

@app.route('/my_requests')
@active_required
def my_requests():
    user_email = session['user'].get('preferred_username').lower()
    current_user = User.query.filter_by(email=user_email).first()   
    
    if not session.get("user"):
        return redirect(url_for("login"))
    if not current_user:
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('login'))
     
    requests = Request.query.filter_by(requester_id=current_user.id).order_by(Request.created_at.desc()).all()
    return render_template('my_requests.html', requests=requests)

@app.route('/available_forms')
@active_required
def available_forms():
    """Display all available request forms"""
    if not session.get("user"):
        return redirect(url_for("login"))
    
    # Get all request types from the database
    form_types = RequestType.query.all()
    
    return render_template('available_forms.html', form_types=form_types)


# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True, port=50010)
