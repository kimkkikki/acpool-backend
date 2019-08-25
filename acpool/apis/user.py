from flask import Blueprint, request, session, send_file
from flask.globals import g
from acpool.models import Users, EmailVerify, db
from common.acpool_response import response
from common.decorator import login_required
from common.send_mail import send_verify_email, generate_random_string, send_password_reset_email, send_temp_password_email
import re
import hashlib
import qrcode
from io import BytesIO
import random
import string
import pyotp
import requests
from sqlalchemy import or_
import simplejson
from datetime import datetime
from common.utils import check_otp_validation, check_email_code_validation
import os
from common.cache import cache

user_blueprint = Blueprint('user_blueprint', __name__)
OTP_KEY_LENGTH = 32


def check_user_validation(username, password, email):
    if len(username) < 6:
        return False

    if ' ' in username:
        return False

    if len(password) < 8:
        return False

    if not re.match("^[a-zA-Z0-9_]*$", username):
        return False

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False

    return True


def check_exist_user(username, email):
    is_exist = Users.query.filter((Users.username == username) | (Users.email == email)).first()
    if is_exist is not None:
        return False
    return True


@user_blueprint.route('/user', methods=['POST'])
def join():
    body = simplejson.loads(request.data)

    if 'username' not in body or 'email' not in body or 'password' not in body:
        return response(error_code=1000)

    username = body['username']
    password = body['password']
    email = body['email']

    if not check_user_validation(username, password, email):
        return response(error_code=1000)

    if not check_recaptcha(body['recaptcha']):
        return response(error_code=1010)

    if not check_exist_user(username, email):
        return response(error_code=1001)

    new_user = Users()
    new_user.username = username
    new_user.email = email
    new_user.password = hashlib.sha256(password.encode()).hexdigest()

    db.session.add(new_user)
    db.session.commit()

    session['username'] = username
    verify_email_send(email, username)

    return response()


@user_blueprint.route('/user', methods=['PUT'])
@login_required
def change_password():
    username = session['username']
    body = simplejson.loads(request.data)

    if 'old_password' not in body or 'new_password' not in body:
        return response(error_code=1000)

    old_password = body['old_password']
    new_password = body['new_password']

    login_user = Users.query.filter(Users.username == username).first()
    hash_old_password = hashlib.sha256(old_password.encode()).hexdigest()
    hash_new_password = hashlib.sha256(new_password.encode()).hexdigest()

    if login_user.password != hash_old_password:
        return response(error_code=1004)

    if hash_old_password == hash_new_password:
        return response(error_code=1005)

    login_user.password = hash_new_password
    db.session.commit()

    # TODO: Password 변경 Email Notification 구현 해야함

    return response()


@user_blueprint.route('/user/email', methods=['PUT'])
@login_required
def change_email_notification():
    username = session['username']
    body = simplejson.loads(request.data)
    email_notification_status = body['emailNotification']

    Users.query.filter(Users.username == username).update({'email_notification': email_notification_status})
    db.session.commit()

    return response()


@user_blueprint.route('/user', methods=['GET'])
@login_required
def get_user():
    _user = Users.query.filter(Users.username == session['username']).first()
    g.user = _user
    return response(_user.to_json())


@user_blueprint.route('/user/otp/qrcode', methods=['GET'])
@login_required
def generate_otp_key_and_get_qr_code():
    user = Users.query.filter(Users.username == session['username']).first()
    if user.otp_key is None or len(user.otp_key) == 0:
        # generate OTP KEY
        user.otp_key = ''.join(random.SystemRandom().choice(string.ascii_letters) for _ in range(OTP_KEY_LENGTH))
        db.session.commit()

    if user.otp_state is False:
        # generate QR code
        qr_code = pyotp.totp.TOTP(user.otp_key).provisioning_uri(user.username, issuer_name="ACPool")
        q = qrcode.make(qr_code)
        img = BytesIO()
        q.save(img)
        img.seek(0)
        return send_file(img, mimetype="image/png")
    return response()


@user_blueprint.route('/user/otp', methods=['POST'])
@login_required
def check_otp_code():
    username = session['username']
    body = simplejson.loads(request.data)

    if 'code' not in body:
        return response(error_code=1000)

    code = body['code']
    try:
        is_valid = check_otp_validation(username, code)
    except ValueError:
        return response(error_code=1006)

    user = Users.query.filter(Users.username == session['username']).first()
    if is_valid is True:
        user.otp_state = True
        db.session.commit()
        return response()

    return response(error_code=1006)


def check_recaptcha(recaptcha_response) -> bool:
    if recaptcha_response == '':
        return False

    recaptcha_params = {'secret': os.getenv("RECAPTCHA_SECRET"), 'response': recaptcha_response}
    recaptcha_result = requests.post('https://www.google.com/recaptcha/api/siteverify', data=recaptcha_params)

    if recaptcha_result.status_code != 200 or simplejson.loads(recaptcha_result.content)['success'] is not True:
        return False

    return True


@user_blueprint.route('/login', methods=['POST'])
def login():
    body = simplejson.loads(request.data)
    if 'username' not in body or 'password' not in body:
        return response(error_code=1000)

    if not check_recaptcha(body['recaptcha']):
        return response(error_code=1010)

    username = body['username']
    password = body['password']
    hash_password = hashlib.sha256(password.encode()).hexdigest()

    login_user = Users.query.filter(or_(Users.username == username, Users.email == username)). \
        filter(Users.password == hash_password).first()

    if login_user is None:
        return response(error_code=1002)

    session['username'] = login_user.username
    return response()


def verify_email_send(email, username):
    # TODO balance 에서 또 보내는 경우에 대한 처리 필요
    _already_send = EmailVerify.query.filter(EmailVerify.username == username).first()
    if _already_send is not None:
        total_seconds = (datetime.utcnow() - _already_send.created).total_seconds()
        if total_seconds < 600:
            return response(error_code=1013)

    if not os.getenv("DEBUG") == 'true':
        verify_code = send_verify_email(email, username)
    else:
        verify_code = generate_random_string()
        print(verify_code)

    if verify_code is not None:
        if _already_send is not None:
            email_verify = _already_send
        else:
            email_verify = EmailVerify()
        email_verify.verify_code = verify_code
        email_verify.username = username
        email_verify.created = datetime.utcnow()

        if _already_send is None:
            db.session.add(email_verify)
        db.session.commit()

        return email_verify


@user_blueprint.route('/user/verify', methods=['GET'])
@login_required
def get_verify_email():
    username = session['username']

    _already_send = EmailVerify.query.filter(EmailVerify.username == username).first()
    if _already_send is not None:
        total_seconds = (datetime.utcnow() - _already_send.created).total_seconds()
        if total_seconds < 600:
            return response(error_code=1013)

    _user = g.user

    verify_code = verify_email_send(_user.email, _user.username)
    if verify_code is not None:
        return response()

    return response(error_code=1014)


@user_blueprint.route('/user/verify', methods=['POST'])
@login_required
def verify_email():
    username = session['username']

    _body = simplejson.loads(request.data)
    is_valid_code = check_email_code_validation(username, _body['verify_code'])

    if is_valid_code is False:
        return response(error_code=1012)

    user = g.user
    user.state = 'normal'
    db.session.commit()

    return response()


@user_blueprint.route('/logout')
def logout():
    session.pop('username', None)
    return response()


@user_blueprint.route('/user/forget', methods=['POST'])
def forget():
    _body = simplejson.loads(request.data)

    if 'recaptcha' not in _body or not check_recaptcha(_body['recaptcha']):
        return response(error_code=1010)

    username = _body['username']
    _user = Users.query.filter(or_(Users.username == username, Users.email == username)).first()
    if _user is None:
        return response(error_code=1018)

    uri = send_password_reset_email(_user.email, _user.username)
    if uri is None:
        return response(error_code=1013)

    cache.set(uri, _user.username, timeout=3600)

    return response()


@user_blueprint.route('/user/forget/<uuid>')
def password_reset(uuid):
    username = cache.get(uuid)

    if username is None:
        return response(error_code=1000)

    temp_password = generate_random_string()
    _user = Users.query.filter(Users.username == username).first()
    _user.password = hashlib.sha256(temp_password.encode()).hexdigest()
    db.session.commit()

    if send_temp_password_email(_user.email, _user.username, temp_password) is None:
        return response(error_code=1013)

    cache.delete(uuid)

    return response()
