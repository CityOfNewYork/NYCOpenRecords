from datetime import datetime

import pyotp
from flask import flash, redirect, request, render_template, session, url_for
from flask_login import current_user, login_required

from app.constants import event_type
from app.lib.db_utils import create_object, update_object
from app.lib.fernet_utils import decrypt_string, encrypt_string
from app.mfa import mfa
from app.mfa.forms import RegisterMFAForm, VerifyMFAForm
from app.models import Events, MFA


@mfa.route('/', methods=['GET', 'POST'])
@login_required
def register():
    form = RegisterMFAForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            device_name = form.device_name.data
            secret = form.mfa_secret.data

            create_object(
                MFA(
                    user_guid=current_user.guid,
                    secret=encrypt_string(secret),
                    device_name=device_name,
                    is_valid=True,
                )
            )
            create_object(
                Events(
                    request_id=None,
                    user_guid=current_user.guid,
                    type_=event_type.MFA_DEVICE_ADDED,
                    timestamp=datetime.utcnow(),
                    new_value={'device_name': device_name, 'is_valid': True},
                )
            )
            return redirect(url_for('mfa.verify'))
    else:
        mfa_secret = pyotp.random_base32()
        qr_uri = pyotp.totp.TOTP(mfa_secret).provisioning_uri(name=current_user.email,
                                                              issuer_name='OpenRecords')
        form.mfa_secret.data = mfa_secret
        return render_template('mfa/register.html',
                               form=form,
                               mfa_secret=mfa_secret,
                               qr_uri=qr_uri)


@mfa.route('/verify', methods=['GET', 'POST'])
@login_required
def verify():
    form = VerifyMFAForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            mfa = MFA.query.filter_by(user_guid=current_user.guid,
                                      device_name=form.device.data,
                                      is_valid=True).one_or_none()

            secret_str = decrypt_string(mfa.secret)
            pyotp_verify = pyotp.TOTP(secret_str).verify(form.code.data)
            if pyotp_verify:
                session['mfa_verified'] = True
                return redirect(url_for('main.index', fresh_login=True))
            flash("Invalid code. Please try again.", category='danger')
            form.code.data = ''
            return render_template('mfa/verify.html',
                                   form=form)
    else:
        mfa = MFA.query.filter_by(user_guid=current_user.guid,
                                  is_valid=True).first()
        if mfa is None:
            return redirect(url_for('mfa.register'))
        return render_template('mfa/verify.html',
                               form=form)


@mfa.route('/manage', methods=['GET'])
@login_required
def manage():
    mfas = MFA.query.filter_by(user_guid=current_user.guid,
                               is_valid=True).all()
    return render_template('mfa/manage.html',
                           mfas=mfas)


@mfa.route('/remove', methods=['POST'])
@login_required
def remove():
    device_name = request.form.get('device-name')
    mfa = MFA.query.filter_by(user_guid=current_user.guid,
                              device_name=device_name,
                              is_valid=True).one_or_none()
    if mfa is not None:
        update_object(
            {'is_valid': False},
            MFA,
            mfa.id
        )
        create_object(
            Events(
                request_id=None,
                user_guid=current_user.guid,
                type_=event_type.MFA_DEVICE_REMOVED,
                timestamp=datetime.utcnow(),
                previous_value={'device_name': device_name, 'is_valid': True},
                new_value={'device_name': device_name, 'is_valid': False},
            )
        )
        flash('The device was removed.', category='success')
    else:
        flash('Something went wrong. Please try again.', category='danger')
    return redirect(url_for('mfa.manage'))
