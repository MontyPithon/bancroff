from app import create_app
from models import db, Request
import json

app = create_app()

with app.app_context():
    # Check recent requests
    requests = Request.query.order_by(Request.id.desc()).limit(2).all()
    
    for req in requests:
        print(f"\nRequest ID: {req.id}")
        print(f"Title: {req.title}")
        print(f"Status: {req.status}")
        print("Form Data:")
        print(json.dumps(req.form_data, indent=2))
        print("-" * 50) 