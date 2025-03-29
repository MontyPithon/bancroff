from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email

class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[
        ('basic_user', 'Basic User'),
        ('admin', 'Administrator'),
        ('dean', 'Dean'),
        ('advisor', 'Advisor'),
        ('chair', 'Chair')
    ])
    status = SelectField('Status', choices=[('active', 'Active'), ('deactivated', 'Deactivated')])
    submit = SubmitField('Submit') 