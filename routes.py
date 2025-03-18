from flask import render_template, redirect, url_for, flash, request, session
from app import app, db
from models import User, Role, Permission, RolePermission
from forms import UserForm
from utils import add_fake_data, admin_required, active_required
import msal
import uuid

@app.route('/')
def index():
    print(session) 
    return render_template('index.html')

@app.route('/users')
@admin_required
@active_required
def user_list():
    if not session.get("user"):
        return redirect(url_for("login"))
    users = User.query.all()
    return render_template('user_list.html', users=users)

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

@app.route("/login")
def login():
    return render_template('login.html')

@app.route("/start_login")
def start_login():
    session["state"] = str(uuid.uuid4())
    auth_url = _build_auth_url(session["state"])
    return redirect(auth_url)

def _build_auth_url(state):
    msal_app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPE,
        state=state,
        redirect_uri=url_for("authorized", _external=True)
    )
    return auth_url

@app.route(REDIRECT_PATH)
def authorized():
    if request.args.get("state") != session.get("state"):
        return redirect(url_for("index"))

    if "error" in request.args:
        return f"Authentication error: {request.args.get('error')}"

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
        session["user"] = result.get("id_token_claims")

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
            session["role"] = "admin"
            session["status"] = "active"
        else:
            session["role"] = user.role.name
            session["status"] = user.status

        return redirect(url_for("index"))
    
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
