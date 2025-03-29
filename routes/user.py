from flask import render_template, redirect, url_for, flash, session, request
from models import db, User, Role
from forms import UserForm
from utils.auth_helpers import admin_required, active_required
import config

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

    @app.route('/upload_signature', methods=['GET', 'POST'])
    def upload_signature():
        from werkzeug.utils import secure_filename
        import os
        from utils.auth_helpers import allowed_file
        
        if not session.get("user"):
            return redirect(url_for("login"))
            
        if request.method == 'POST':
            # Check if the file part is present in the request
            if 'signature' not in request.files:
                flash('No file part in the request')
                return redirect(request.url)
            
            file = request.files['signature']
            
            # Check if a file was selected
            if file.filename == '':
                flash('No file selected')
                return redirect(request.url)
            
            # Validate and save the file
            if file and allowed_file(file.filename, config.ALLOWED_EXTENSIONS):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                flash('Signature uploaded successfully')
                return redirect(url_for('index'))

        # Render the upload form (GET request)
        return render_template('upload_signature.html') 