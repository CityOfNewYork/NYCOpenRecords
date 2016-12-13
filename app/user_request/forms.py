from flask_wtf import Form
from wtforms import SelectField


class RemoveUserRequestForm(Form):
    user = SelectField('Users')

    def __init__(self, agency_users):
        super(RemoveUserRequestForm, self).__init__()
        self.user.choices = [
            (agency_user.guid, ', '.join([agency_user.last_name, agency_user.first_name]))
            for agency_user in agency_users
        ]