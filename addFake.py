from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'password'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bancroff.db'

db = SQLAlchemy(app)

#db models
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


with app.app_context():
    try:
        db.create_all()

        # roles
        roles = [
            Role(name='admin', description='Administrator role with full permissions'),
            Role(name='basic_user', description='Regular user role with limited permissions')
        ]
        db.session.add_all(roles)
        db.session.commit()

        # permissions
        permissions = [
            Permission(name='read', description='Read permission'),
            Permission(name='write', description='Write permission'),
            Permission(name='delete', description='Delete permission')
        ]
        db.session.add_all(permissions)
        db.session.commit()

        # role to perms
        role_permissions = [
            RolePermission(role_id=1, permission_id=1),
            RolePermission(role_id=1, permission_id=2),
            RolePermission(role_id=1, permission_id=3),
            RolePermission(role_id=2, permission_id=1)
        ]
        db.session.add_all(role_permissions)
        db.session.commit()

        # add fake users
        fake_users = [
            User(email='john.smith@gmail.com', full_name='John Smith', status='active', provider_user_id='112233445', provider='Google', role_id=1),
            User(email='emily.johnson@outlook.com', full_name='Emily Johnson', status='active', provider_user_id='EJ789012', provider='Microsoft', role_id=2),
            User(email='michael.brown@yahoo.com', full_name='Michael Brown', status='deactivated', provider_user_id='MB345678', provider='Yahoo', role_id=2),
            User(email='sarah.davis@icloud.com', full_name='Sarah Davis', status='active', provider_user_id='SD901234', provider='Apple', role_id=2),
            User(email='david.wilson@protonmail.com', full_name='David Wilson', status='deactivated', provider_user_id='DW567890', provider='ProtonMail', role_id=2)
        ]
        db.session.add_all(fake_users)
        db.session.commit()

        print("Fake data added successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")
        db.session.rollback()