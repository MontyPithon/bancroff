from flask import render_template, redirect, url_for, flash, request, session
from models import db, User, Role
from utils.auth_helpers import build_auth_url, get_token_from_code
import config

def setup_auth_routes(app):
    @app.route("/login")
    def login():
        return render_template('login.html')

    @app.route("/start_login")
    def start_login():
        auth_url = build_auth_url(
            config.CLIENT_ID, 
            config.AUTHORITY, 
            config.SCOPE, 
            url_for("authorized", _external=True)
        )
        return redirect(auth_url)

    @app.route(config.REDIRECT_PATH)
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
            result = get_token_from_code(
                config.CLIENT_ID,
                config.CLIENT_SECRET,
                config.AUTHORITY,
                code,
                config.SCOPE,
                url_for("authorized", _external=True)
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

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index")) 