from itertools import groupby
from operator import itemgetter
from sqlalchemy import or_

from app.models import (
    Agencies,
    LetterTemplates,
    Reasons
)


def get_active_users_as_choices(agency_ein):
    """
    Retrieve a list of users that are active for a given agency
    :param agency_ein: Agency EIN (String)
    :return: A list of user tuples (id, name)
    """
    active_users = sorted(
        [(user.get_id(), user.name)
         for user in Agencies.query.filter_by(ein=agency_ein).one().active_users],
        key=lambda x: x[1])
    active_users.insert(0, ('', 'All'))
    return active_users


def get_reasons(agency_ein, reason_type=None):
    """Retrieve the determination reasons (used in emails) for the specified agency as a JSON object. If reason_type is
    provided, only retrieve determination_reasons of that type.

    Args:
        agency_ein (str): Agency EIN
        reason_type (str): One of ("denial", "closing", "re-opening")

    Returns:
        dict:
            {
                'type_', [(reason_id, reason_title),...]
            }

    """
    if reason_type is not None:
        reasons = Reasons.query.with_entities(Reasons.id, Reasons.title, Reasons.type).filter(
            Reasons.type == reason_type,
            or_(Reasons.agency_ein == agency_ein, Reasons.agency_ein == None)
        ).all()
    else:
        reasons = Reasons.query.with_entities(Reasons.id, Reasons.title, Reasons.type).filter(
            or_(Reasons.agency_ein == agency_ein, Reasons.agency_ein == None)
        ).all()

    reasons = list(_group_tuples(reasons))

    reasons_dict = {}

    for i in reasons:
        type_ = i[0]
        vals = i[1]

        reasons_dict[type_] = []

        for i in vals:
            reasons_dict[type_].append((i[0], i[1]))

    if reason_type is not None:
        return reasons_dict[reason_type]
    return reasons_dict


def get_letter_templates(agency_ein, template_type=None):
    """
    Retrieve letter templates for the specified agency as a JSON object. If template type is provided, only get
    templates of that type.

    :param agency_ein: Agency EIN (String)
    :param template_type: One of "acknowledgment", "denial", "closing", "letter", "extension", "re-opening" (String)
    :return: Dictionary

        {
            'type_': [(template_id, template_name),...]
        }
    """
    if template_type is not None:
        templates = LetterTemplates.query.with_entities(LetterTemplates.id, LetterTemplates.title,
                                                        LetterTemplates.type_).filter(
            LetterTemplates.type_ == template_type).all()
    else:
        templates = LetterTemplates.query.with_entities(LetterTemplates.id, LetterTemplates.title,
                                                        LetterTemplates.type_).filter_by(agency_ein=agency_ein).all()

    templates = list(_group_tuples(templates))

    template_dict = {}

    for i in templates:
        type_ = i[0]
        vals = i[1]

        template_dict[type_] = []

        for i in vals:
            template_dict[type_].append((i[0], i[1]))

    if template_type is not None:
        return template_dict[template_type]
    return template_dict


def _group_tuples(tuples):
    """
    Group a list of templates by their type
    :param tuples: List of templates (template.id, template.title, template.type_)
    :return: a generator containing each grouped template type
    """
    grouped = groupby(tuples, itemgetter(2))

    for key, sub_iter in grouped:
        yield key, list(sub_iter)
