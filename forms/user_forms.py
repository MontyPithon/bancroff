from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, SubmitField, SelectField, FileField

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

class SignatureUploadForm(FlaskForm):
    signature = FileField('Your Signature', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Upload Signature')