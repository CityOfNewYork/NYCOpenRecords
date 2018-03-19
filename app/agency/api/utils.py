from app.models import Agencies


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
