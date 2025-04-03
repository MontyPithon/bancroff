import uuid
import msal
from flask import url_for, session
from functools import wraps
from flask import redirect, flash, url_for

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

def management_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        allowed_roles = ["admin", "chair", "dean", "advisor"]
        if session.get("role") not in allowed_roles:
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

def build_auth_url(client_id, authority, scope, redirect_uri):
    session["state"] = str(uuid.uuid4())
    msal_app = msal.ConfidentialClientApplication(
        client_id, authority=authority, client_credential=None
    )
    auth_url = msal_app.get_authorization_request_url(
        scopes=scope,
        state=session["state"],
        redirect_uri=redirect_uri
    )
    return auth_url

def get_token_from_code(client_id, client_secret, authority, code, scope, redirect_uri):
    msal_app = msal.ConfidentialClientApplication(
        client_id, authority=authority, client_credential=client_secret
    )
    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=scope,
        redirect_uri=redirect_uri
    )
    return result

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_user_signature(user_id):
    from models import UserSignature
    signature = UserSignature.query.filter_by(
        user_id=user_id,
        is_active=True
    ).order_by(UserSignature.uploaded_at.desc()).first()
    
    return signature 