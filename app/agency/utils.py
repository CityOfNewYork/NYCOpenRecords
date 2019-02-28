from datetime import datetime

from flask_login import current_user

from app.lib.utils import eval_request_bool
from app.lib.db_utils import (
    update_object,
    create_object
)
from app.models import (
    Agencies,
    Events,
    AgencyUsers
)
from app.constants.event_type import (
    AGENCY_ACTIVATED,
    AGENCY_DEACTIVATED,
    AGENCY_USER_DEACTIVATED
)


def update_agency_active_status(agency_ein, is_active):
    """
    Update the active status of an agency.
    :param agency_ein: String identifier for agency (4 characters)
    :param is_active: Boolean value for agency active status (True = Active)
    :return: Boolean value (True if successfully changed active status)
    """
    agency = Agencies.query.filter_by(ein=agency_ein).first()
    is_valid_agency = agency is not None
    activate_agency = eval_request_bool(is_active)

    if is_active is not None and is_valid_agency:
        update_object(
            {'is_active': activate_agency},
            Agencies,
            agency_ein
        )
        if activate_agency:
            create_object(
                Events(
                    request_id=None,
                    user_guid=current_user.guid,
                    type_=AGENCY_ACTIVATED,
                    previous_value={"ein": agency_ein, "is_active": "False"},
                    new_value={"ein": agency_ein, "is_active": "True"},
                    timestamp=datetime.utcnow()
                )
            )
            # create request documents
            for request in agency.requests:
                request.es_create()

            return True
        else:
            create_object(
                Events(
                    request_id=None,
                    user_guid=current_user.guid,
                    type_=AGENCY_DEACTIVATED,
                    previous_value={"ein": agency_ein, "is_active": "True"},
                    new_value={"ein": agency_ein, "is_active": "False"},
                    timestamp=datetime.utcnow()
                )
            )
            # remove requests from index
            for request in agency.requests:
                request.es_delete()
            # deactivate agency users
            for user in agency.active_users:
                update_object(
                    {"is_agency_active": "False",
                     "is_agency_admin": "False"},
                    AgencyUsers,
                    (user.guid, agency_ein)
                )
                create_object(
                    Events(
                        request_id=None,
                        user_guid=current_user.guid,
                        type_=AGENCY_USER_DEACTIVATED,
                        previous_value={"user_guid": user.guid,
                                        "ein": agency_ein,
                                        "is_active": "True"},
                        new_value={"user_guid": user.guid,
                                   "ein": agency_ein,
                                   "is_active": "False"},
                        timestamp=datetime.utcnow()
                    )
                )

            return True
    return False


def get_agency_feature(agency_ein, feature):
    """
    Retrieve the specified agency feature for the specified agency.

    :param agency_ein:  String identifier for agency (4 characters)
    :param feature: Feature specified. See app/lib/constants/agency_features.py for possible values (String)

    :return: JSON Object
    """

    agency_features = get_agency_features(agency_ein)

    if agency_features is not None and feature in agency_features:
        return {feature: agency_features[feature]}

    return None


def get_agency_features(agency_ein):
    """
    Retrieve the agency features JSON object for the specified agency.

    :param agency_ein: String identifier for agency (4 characters)
    :return: JSON Object
    """
    is_valid_agency = Agencies.query.filter_by(ein=agency_ein).first() is not None

    if is_valid_agency:
        agency_features = Agencies.query.filter_by(ein=agency_ein).first().agency_features

        return agency_features

    return None
