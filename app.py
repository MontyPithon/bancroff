from flask import Flask, render_template, redirect, url_for, flash, request, session
import msal
import uuid
from flask_sqlalchemy import SQLAlchemy
import os
from models import User, Role, Permission, RolePermission
from forms import UserForm
from utils import add_fake_data, admin_required, active_required
import routes

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

# create database with fake data
if not os.path.exists('./instance/bancroff.db'):
    with app.app_context():
        print('test')
        db.create_all()
        add_fake_data()

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True, port=50010)
