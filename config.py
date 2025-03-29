import os

# Microsoft OAuth settings
CLIENT_ID = "1daa4a2e-7a38-4225-854c-45d232e9ccbf"
CLIENT_SECRET = "zjo8Q~N4HOF61PaaHwEOVGwLMFH6vondPFxWPcjN"
AUTHORITY = "https://login.microsoftonline.com/170bbabd-a2f0-4c90-ad4b-0e8f0f0c4259"
REDIRECT_PATH = "/getAToken"
SCOPE = ["User.Read"]

# Flask settings
SECRET_KEY = 'password'
DEBUG = True

# Database settings
SQLALCHEMY_DATABASE_URI = 'sqlite:///bancroff.db'

# File upload settings
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Development settings
SERVER_PORT = 50010
