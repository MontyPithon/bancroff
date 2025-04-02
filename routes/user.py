from flask import render_template, redirect, url_for, flash, session, request
from models import db, User, Role, UserSignature
from forms import UserForm
from utils.auth_helpers import admin_required, active_required
from forms.user_forms import SignatureUploadForm
import config
from werkzeug.utils import secure_filename
import os
def setup_user_routes(app):
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
                    current_user_email = session['user'].get('preferred_username').lower()
                    current_user = User.query.filter_by(email=current_user_email).first() 
                    user.full_name = form.name.data
                    user.email = form.email.data
                    user.role = Role.query.filter_by(name=form.role.data).first()
                    
                    if current_user and current_user.id == user_id and form.status.data == 'deactivated':
                        flash('You cannot deactivate your own account!', 'danger')
                        user.status = 'active'  # Force active status for own account
                    else:
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
                form.role.data = user.role.name if user.role else 'basic_user'
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
            if user:
                current_user_email = session['user'].get('preferred_username').lower()
                current_user = User.query.filter_by(email=current_user_email).first()
                if current_user and current_user.id == user_id:
                    flash('You cannot delete your own account!', 'danger')
                else:
                    db.session.delete(user)
                    db.session.commit()
                    flash('User deleted successfully!', 'success')
            else:
                flash('User not found!', 'danger')
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
                current_user_email = session['user'].get('preferred_username').lower()
                current_user = User.query.filter_by(email=current_user_email).first()
                
                if current_user and current_user.id == user_id:
                    flash('You cannot deactivate your own account!', 'danger')
                else:
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

    @app.route('/upload_signature', methods=['GET', 'POST'])
    @active_required
    def upload_signature():
        if not session.get("user"):
            return redirect(url_for("login"))
            
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        # Get the current active signature
        from utils.auth_helpers import get_user_signature
        active_signature = get_user_signature(current_user.id)
        
        form = SignatureUploadForm()
        
        if form.validate_on_submit():
            filename = secure_filename(form.signature.data.filename)
            
            # Create unique filename with user ID and timestamp
            import time 
            file_ext = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"signature_{current_user.id}_{int(time.time())}.{file_ext}"
            
            # Save the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            form.signature.data.save(file_path)
            
            # Deactivate all previous signatures
            for sig in current_user.signatures:
                sig.is_active = False
            
            # Create new signature record
            new_signature = UserSignature(
                user_id=current_user.id,
                signature_image_path=unique_filename,
                is_active=True
            )
            
            # Update user's primary signature path
            current_user.signature_path = unique_filename
            
            db.session.add(new_signature)
            db.session.commit()
            
            flash('Signature uploaded successfully!', 'success')
            return redirect(url_for('index'))
        
        return render_template('upload_signature.html', form=form, active_signature=active_signature)