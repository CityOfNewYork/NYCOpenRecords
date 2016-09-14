from models import *


def create_request(id=id, agency=None, summary=None, text=None, user_id=None,
                   offline_submission_type=None,
                   date_received=None):


    """ Create a Request object and return the ID. """
    agency_id = Agency.query.filter_by(name=agency).first().id
    req = Request(id=id, agency=agency_id, summary=summary, text=text, creator_id=user_id,
                  offline_submission_type=offline_submission_type, date_received=date_received)
    db.session.add(req)
    db.session.commit()
    req.set_due_date()
    return req.id


def set_due_date(self):
    if not self.date_received:
        self.date_received = self.date_created
    if self.extended == True:
        self.due_date = cal.addbusdays(cal.adjust(self.date_received, FOLLOWING),
                                       int(app.config['DAYS_AFTER_EXTENSION']))
        if self.date_received.hour > 17:
            self.due_date = cal.addbusdays(self.due_date, 1)
    else:
        self.due_date = cal.addbusdays(cal.adjust(self.date_received, FOLLOWING), int(app.config['DAYS_TO_FULFILL']))
        if self.date_received.hour > 17:
            self.due_date = cal.addbusdays(self.due_date, 1)