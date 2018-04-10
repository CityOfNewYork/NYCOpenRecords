from app.models import (
    Agencies,
    LetterTemplates
)

from app.constants.letter_type import letter_type
from itertools import groupby
from operator import itemgetter


def get_active_users_as_choices(agency_ein):
    """

    :param agency_ein:
    :return:
    """
    active_users = sorted(
        [(user.get_id(), user.name)
         for user in Agencies.query.filter_by(ein=agency_ein).one().active_users],
        key=lambda x: x[1])
    active_users.insert(0, ('', 'All'))
    return active_users


def get_letter_templates(agency_ein, template_type=None):
    """
    Retrieve letter templates for the specified agency as a JSON object. If template type is provided, only get
    templates of that type.

    :param agency_ein: Agency EIN (String)
    :param template_type: One of "acknowledgment", "denial", "closing", "letter", "extension" (String)
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

    templates = list(_group_templates(templates))

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


def _group_templates(templates):
    """

    :param templates: List of templates (template.id, template.title, template.type_)
    :return:
    """
    grouped = groupby(templates, itemgetter(2))

    for key, sub_iter in grouped:
        yield key, list(sub_iter)
