from flask import Flask
from flask.ext.wtf import Form
from flask_recaptcha import ReCaptcha
from wtforms import StringField, SelectField, TextAreaField, DateField, \
    BooleanField, PasswordField, SubmitField, FileField
from wtforms.validators import DataRequired, Length, Email
# from wtforms_components import

class LoginForm(Form):
    username = StringField('Email', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

    class Meta:
        # This overrides the value from the base form.
        csrf = False