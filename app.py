from flask import Flask, render_template, redirect, url_for, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email

# Initialize the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'password'  # Secret key for session management

# Enable debug mode for detailed error messages
app.debug = True

# Set up the SQLite database here




# Initialize the database and migration tool


# Define the User model for the database (Teammate 1 needs to complete this part)

# Mock data (to be replaced with actual database logic)
users = []

# Define the UserForm for creating and updating users
class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])  # Name field, required
    email = StringField('Email', validators=[DataRequired(), Email()])  # Email field, required and must be a valid email
    role = SelectField('Role', choices=[('basicuser', 'Basic User'), ('admin', 'Administrator')])  # Role selection
    status = SelectField('Status', choices=[('active', 'Active'), ('deactivated', 'Deactivated')])  # Status selection
    submit = SubmitField('Submit')  # Submit button

# Route for the home page
@app.route('/')
def index():
    return render_template('index.html')

# Route for displaying the list of users
@app.route('/users')
def user_list():
    # Teammate 1: Replace mock data with database query
    # users = User.query.all()
    return render_template('user_list.html', users=users)

# Route for creating a new user
@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    form = UserForm()
    if form.validate_on_submit():
        try:
            # Teammate 1: Replace mock user creation logic with database insertion
            
            new_user = {
                'id': len(users) + 1,
                'name': form.name.data,
                'email': form.email.data,
                'role': form.role.data,
                'status': form.status.data
            }
            users.append(new_user)
            flash('User created successfully!', 'success')
            return redirect(url_for('user_list'))
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
    return render_template('create_user.html', form=form)

# Route for updating an existing user
@app.route('/update_user/<int:user_id>', methods=['GET', 'POST'])
def update_user(user_id):
    form = UserForm()
    user = next((u for u in users if u['id'] == user_id), None)
    # Teammate 1: Replace mock logic with database query
    if user:
        if form.validate_on_submit():
            try:
                # Teammate 1: Replace mock user update logic with database update
                user['name'] = form.name.data
                user['email'] = form.email.data
                user['role'] = form.role.data
                user['status'] = form.status.data
                flash('User updated successfully!', 'success')
                return redirect(url_for('user_list'))
            except Exception as e:
                flash(f'An error occurred: {str(e)}', 'danger')
        else:
            form.name.data = user['name']
            form.email.data = user['email']
            form.role.data = user['role']
            form.status.data = user['status']
    else:
        flash('User not found!', 'danger')
        return redirect(url_for('user_list'))
    return render_template('update_user.html', form=form)

# Route for deleting a user
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    global users
    try:
        # Teammate 1: Replace mock deletion logic with database deletion
        
        users = [u for u in users if u['id'] != user_id]
        flash('User deleted successfully!', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
    return redirect(url_for('user_list'))

# Route for deactivating a user
@app.route('/deactivate_user/<int:user_id>', methods=['POST'])
def deactivate_user(user_id):
    try:
        user = next((u for u in users if u['id'] == user_id), None)
        # Teammate 1: Replace mock logic with database query and update
        if user:
            user['status'] = 'deactivated'
            flash('User deactivated successfully!', 'success')
        else:
            flash('User not found!', 'danger')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
    return redirect(url_for('user_list'))

# Route for reactivating a user
@app.route('/reactivate_user/<int:user_id>', methods=['POST'])
def reactivate_user(user_id):
    try:
        user = next((u for u in users if u['id'] == user_id), None)
        # Teammate 1: Replace mock logic with database query and update
        if user:
            user['status'] = 'active'
            flash('User reactivated successfully!', 'success')
        else:
            flash('User not found!', 'danger')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
    return redirect(url_for('user_list'))

# Teammate 2: Add Office365 authentication routes and logic here

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)