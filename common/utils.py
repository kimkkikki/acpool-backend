from datetime import datetime, timedelta
from acpool.rpc.handler import send
from acpool.models import Users, Coins, EmailVerify, db
from werkzeug.contrib.cache import SimpleCache
import os
from random import randint
import simplejson
import pyotp
import logging

logger = logging.getLogger(__name__)
cache = SimpleCache()


def convert_hashrate_by_share(algorithm, sum_of_share):
    if sum_of_share is None:
        sum_of_share = 0

    if algorithm in ['equihash', 'zhash']:
        hashrate = float("{0:.2f}".format(sum_of_share * 16.384))
    else:
        hashrate = float("{0:.2f}".format(sum_of_share * 7158388.055))

    return hashrate


def hashrate_to_readable_string(hashrate, hash_type=None):
    hash_string = 'H'
    if hash_type == 'equihash' or hash_type == 'zhash':
        hash_string = 'Sol'

    if hashrate > 1000000000000:
        return '{0:.2f} T%s/s'.format(hashrate / 1000000000000) % hash_string
    elif hashrate > 1000000000:
        return '{0:.2f} G%s/s'.format(hashrate / 1000000000) % hash_string
    elif hashrate > 1000000:
        return '{0:.2f} M%s/s'.format(hashrate / 1000000) % hash_string
    elif hashrate > 1000:
        return '{0:.2f} K%s/s'.format(hashrate / 1000) % hash_string
    else:
        return '{0:.2f} %s/s'.format(hashrate) % hash_string


def get_chart_start_end_datetime() -> (datetime, datetime):
    yesterday = datetime.utcnow() - timedelta(days=1)
    yesterday = yesterday.replace(second=0, microsecond=0, minute=(yesterday.minute - (yesterday.minute % 10)))
    now = datetime.utcnow()
    now = now.replace(second=0, microsecond=0, minute=(now.minute - (now.minute % 10)))

    return yesterday, now


def check_address_validation(coin_name, address):
    coin = Coins.query.filter(Coins.name == coin_name).first()

    if coin is None:
        return False

    try:
        response_data = send(os.getenv("RPC_HOST"), coin.port, randint(0, 9), 'web.validate.address', address)
        result_data = simplejson.loads(response_data)
    except ConnectionRefusedError:
        return False

    if result_data['error'] is not None or result_data['result']['isvalid'] is None:
        return False
    return result_data['result']['isvalid']


def check_otp_validation(username, otp_code):
    user = Users.query.filter(Users.username == username).first()
    otp_key = user.otp_key
    code = otp_code
    try:
        int(code)
        t = pyotp.TOTP(otp_key)
        is_valid = t.verify(code)
        return is_valid

    except ValueError:
        return False


def check_email_code_validation(username, email_code):
    email_verify = EmailVerify.query.filter(EmailVerify.username == username).first()
    if email_verify is None or email_verify.verify_code != email_code:
        return False
    else:
        db.session.delete(email_verify)
        db.session.commit()
        return True


def translate_float_string(num: float):
    for i in reversed(range(8)):
        temp_int = int(num * 10000000) % pow(10, i)
        if temp_int == 0:
            return ('{0:.%df}' % (7 - i)).format(num)
