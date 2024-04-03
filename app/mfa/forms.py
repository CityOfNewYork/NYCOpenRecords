from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField, StringField
from wtforms.validators import (
    Length,
    DataRequired,
)

from app.models import MFA


class RegisterMFAForm(FlaskForm):
    device_name = StringField('Device Name', validators=[Length(max=32), DataRequired()])
    mfa_secret = HiddenField(validators=[Length(max=32), DataRequired()])


class VerifyMFAForm(FlaskForm):
    device = SelectField('Device', validators=[DataRequired()])
    code = StringField('Code', validators=[Length(min=6, max=6), DataRequired()])

    def __init__(self):
        super(VerifyMFAForm, self).__init__()

        self.device.choices = [
            (mfa.device_name,
             mfa.device_name) for mfa in MFA.query.filter_by(user_guid=current_user.guid,
                                                             is_valid=True).all()
        ]
        self.device.choices.insert(0, ('', ''))
