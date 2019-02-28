from app.models import AgencyUsers, Users


def get_agency_active_users(agency_ein):
    """
    Retrieve a list of active users for the specified agency.
    :param agency_ein: Agency EIN
    :return: List
    """
    active_users_guids = AgencyUsers.query.with_entities(AgencyUsers.user_guid).filter_by(
        is_agency_active=True,
        agency_ein=agency_ein
    ).all()
    active_users = []
    for user in active_users_guids:
        active_users.append(
            Users.query.filter(Users.guid == user[0]).one())

    return active_users
