from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email

class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])  # Name field, required
    email = StringField('Email', validators=[DataRequired(), Email()])  # Email field, required and must be a valid email
    role = SelectField('Role', choices=[('basic_user', 'Basic User'), ('admin', 'Administrator')])  # Role selection
    status = SelectField('Status', choices=[('active', 'Active'), ('deactivated', 'Deactivated')])  # Status selection
    submit = SubmitField('Submit')  # Submit button
