from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'password'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bancroff.db'


db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column(db.String(255))
    status = db.Column(db.String(20), default='active', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    provider_user_id = db.Column(db.String(255))
    provider = db.Column(db.String(30))

with app.app_context():
    try:
        fake_users = [
            User(email='john.smith@gmail.com', full_name='John Smith', status='active', provider_user_id='112233445', provider='Google'),
            User(email='emily.johnson@outlook.com', full_name='Emily Johnson', status='active', provider_user_id='EJ789012', provider='Microsoft'),
            User(email='michael.brown@yahoo.com', full_name='Michael Brown', status='deactivated', provider_user_id='MB345678', provider='Yahoo'),
            User(email='sarah.davis@icloud.com', full_name='Sarah Davis', status='active', provider_user_id='SD901234', provider='Apple'),
            User(email='david.wilson@protonmail.com', full_name='David Wilson', status='deactivated', provider_user_id='DW567890', provider='ProtonMail')
        ]

        db.session.add_all(fake_users)
        db.session.commit()
        print("Fake users added successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")