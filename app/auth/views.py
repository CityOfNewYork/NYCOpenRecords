"""
.. module:: auth.views.

   :synopsis: Handles SAML authentication endpoints for NYC OpenRecords
"""
import json

from flask import request, redirect, session, render_template, make_response, url_for
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from app.auth import auth
from app.auth.forms import ManageUserAccountForm
from app.auth.utils import prepare_flask_request, init_saml_auth, create_mailing_address, process_user_data
from app.models import User


@auth.route('/', methods=['GET', 'POST'])
def index():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    errors = []
    not_auth_warn = False
    success_slo = False
    attributes = False
    paint_logout = False

    if 'sso' in request.args:
        return redirect(auth.login())
    elif 'sso2' in request.args:
        return_to = '%sauth/attrs/' % request.host_url
        return redirect(auth.login(return_to))
    elif 'slo' in request.args:
        name_id = None
        session_index = None
        if 'samlNameId' in session:
            name_id = session['samlNameId']
        if 'samlSessionIndex' in session:
            session_index = session['samlSessionIndex']

        return redirect(auth.logout(name_id=name_id, session_index=session_index))
    elif 'acs' in request.args:
        auth.process_response()
        errors = auth.get_errors()
        not_auth_warn = not auth.is_authenticated()
        if len(errors) == 0:
            session['samlUserdata'] = auth.get_attributes()
            session['samlNameId'] = auth.get_nameid()
            session['samlSessionIndex'] = auth.get_session_index()
            self_url = OneLogin_Saml2_Utils.get_self_url(req)
            user = User.query.filter_by(guid=session['samlUserdata']['guid'][0]).first()
            if not user:
                return redirect(url_for('auth.manage_account'))
            if 'RelayState' in request.form and self_url != request.form['RelayState']:
                return redirect(auth.redirect_to(request.form['RelayState']))
    elif 'sls' in request.args:
        dscb = lambda: session.clear()
        url = auth.process_slo(delete_session_cb=dscb)
        errors = auth.get_errors()
        if len(errors) == 0:
            if url is not None:
                return redirect(url)
            else:
                success_slo = True

    if 'samlUserdata' in session:
        paint_logout = True
        if len(session['samlUserdata']) > 0:
            attributes = session['samlUserdata'].items()

    return render_template(
        'auth/index.html',
        errors=errors,
        not_auth_warn=not_auth_warn,
        success_slo=success_slo,
        attributes=attributes,
        paint_logout=paint_logout,
    )


@auth.route('/attrs/')
def attrs():
    paint_logout = False
    attributes = False

    if 'samlUserdata' in session:
        paint_logout = True
        if len(session['samlUserdata']) > 0:
            attributes = session['samlUserdata'].items()

    return render_template('auth/attrs.html', paint_logout=paint_logout,
                           attributes=attributes)


@auth.route('/metadata/')
def metadata():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)

    if len(errors) == 0:
        resp = make_response(metadata, 200)
        resp.headers['Content-Type'] = 'text/xml'
    else:
        resp = make_response(', '.join(errors), 500)
    return resp


@auth.route('/manage', methods=['GET', 'POST'])
def manage_account():
    """

    :return:
    """
    form = ManageUserAccountForm()
    if request.method == 'POST':

        # Get Form Data
        title = form.user_title.data
        organization = form.user_organization.data
        phone = form.phone.data
        fax = form.fax.data
        mailing_address = create_mailing_address(
            address_one=form.address_one.data,
            address_two=form.address_two.data,
            city=form.city.data,
            state=form.state.data,
            zipcode=form.zipcode.data
        )

        # Determine if user needs to be stored in the database or updated
        success = process_user_data(
            guid=session['samlUserdata']['guid'][0],
            title=title,
            organization=organization,
            phone=phone,
            fax=fax,
            mailing_address=mailing_address
        )
        if not success:
            error_message = 'Failed to update your user account. Please contact the OpenRecords support team'
            return render_template('auth/manage_account.html', errors=error_message)

    return render_template('auth/manage_account.html', form=form)
