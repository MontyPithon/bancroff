from faker import Faker
from functools import wraps
from flask import session, flash, redirect, url_for
from models import Role, Permission, RolePermission, User
from app import db

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
