from flask import (
    request,
    jsonify
)
from flask_login import current_user
from app.agency import agency
from app.agency.utils import (
    update_agency_active_status,
    get_agency_features,
    get_agency_feature
)
from app.constants.agency_features import AGENCY_FEATURES


# TODO: Manage agency features within this file.

@agency.route('/<agency_ein>', methods=["PATCH"])
def patch(agency_ein):
    """
    Only accessible by Super Users

    Currently only changes:
        is_active
    """
    if not current_user.is_anonymous and current_user.is_super:
        is_active = request.form.get('is_active')
        update_successful = update_agency_active_status(agency_ein, is_active)
        if update_successful:
            return '', 200
        return '', 400
    return '', 403


@agency.route('/features/<agency_ein>', methods=['GET'])
def agency_features(agency_ein):
    """
    Retrieve the agency features JSON for the specified agency.

    :param agency_ein: Agency EIN (String)

    :return: JSON Object
    """
    agency_features_json = get_agency_features(agency_ein)

    if agency_features_json is not None:
        return jsonify(agency_features_json), 200
    return '', 400


@agency.route('/feature/<agency_ein>/<feature>', methods=['GET'])
def agency_feature(agency_ein, feature):
    """
    Retrieve the information for the specified agency_feature in the specified agency, if exists.
    :param agency_ein: Agency EIN (String)
    :param feature: Feature specified. See app/lib/constants/agency_features for possible values (String)

    :return: JSON Object
    """

    if agency_ein is None:
        return jsonify({'error': 'missing agency ein'}), 400

    if feature is None:
        return jsonify({'error': 'missing agency feature'}), 400

    if feature not in AGENCY_FEATURES:
        return jsonify({'error': 'invalid agency feature'}), 400

    agency_feature_json = get_agency_feature(agency_ein, feature)

    if agency_feature_json is not None:
        return jsonify(agency_feature_json), 200

    return '', 404
