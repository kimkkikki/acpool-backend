from flask import Blueprint, request, session, g
from acpool.models import db, Wallets, Transactions, EmailVerify
import psycopg2
import sqlalchemy.exc
from common.acpool_response import response
from common.decorator import login_required
import simplejson
from common.utils import check_otp_validation, check_email_code_validation
from acpool.rpc.handler import send
import os
from datetime import datetime
from common.send_mail import send_account_change_email
from acpool import querys

wallet_blueprint = Blueprint('wallet_blueprint', __name__)
COUNT_PER_PAGE = 25


def check_address_validation(address: str, coin_name: str) -> bool:
    coin = querys.get_coin_with_coin_name(coin_name)

    # Check Only Production
    if not os.getenv("DEBUG") == 'true':
        validate_address_result = send(os.getenv("RPC_HOST"), coin.port, 0, 'web.validate.address', [address])
        is_validate = simplejson.loads(validate_address_result)

        if is_validate['result'] is None or not is_validate['result']['isvalid']:
            return False

    return True


def check_wallet_form_validation(body):
    if 'coin_name' not in body or 'address' not in body:
        return False

    coin_name = body['coin_name']
    coin_name = coin_name.lower().replace(' ', '-')
    address = body['address']

    if 'payout' in body:
        payout = float(body['payout'])
        if payout != 0 and payout < 0.01:
            return False

    # check valid address
    is_address_valid = check_address_validation(address, coin_name)
    if is_address_valid is False:
        return False

    return True


def check_two_factor_authentication(username, method, code):
    if method == 'otp':
        return check_otp_validation(username, code)
    else:
        return check_email_code_validation(username, code)


@wallet_blueprint.route('/user/wallet', methods=['POST'])
@login_required
def add_wallet():
    username = session['username']
    body = simplejson.loads(request.data)

    authenticate_method = body['authenticate_method']
    authenticate_code = body['authenticate_code']

    if check_two_factor_authentication(username, authenticate_method, authenticate_code):
        if not check_wallet_form_validation(body):
            return response(error_code=1000)

        coin_name = body['coin_name']
        address = body['address']
        label = body['label']
        try:
            new_wallet = Wallets()
            new_wallet.username = username
            new_wallet.coin_name = coin_name
            new_wallet.address = address
            new_wallet.label = label
            new_wallet.type = 'other'
            db.session.add(new_wallet)
            db.session.commit()
            return response()
        except psycopg2.IntegrityError:
            return response(error_code=1009)
        except sqlalchemy.exc.IntegrityError:
            return response(error_code=1009)
        except Exception:
            return response(error_code=1009)

    return response(error_code=1015)


@wallet_blueprint.route('/user/wallet/<wallet_id>', methods=['PUT'])
@login_required
def edit_wallet(wallet_id):
    username = session['username']
    body = simplejson.loads(request.data)

    authenticate_method = body['authenticate_method']
    authenticate_code = body['authenticate_code']

    if check_two_factor_authentication(username, authenticate_method, authenticate_code):
        if not check_wallet_form_validation(body):
            return response(error_code=1000)

        label = body['label']
        address = body['address']
        payout = body['payout']

        target_wallet = Wallets.query.filter(Wallets.username == username).filter(Wallets.id == wallet_id).first()
        if target_wallet is None:
            return response(error_code=1000)
        target_wallet.label = label
        target_wallet.address = address
        target_wallet.payout = payout

        db.session.commit()
        return response()

    return response(error_code=1016)


@wallet_blueprint.route('/user/wallet/<wallet_id>', methods=['DELETE'])
@login_required
def delete_wallet(wallet_id):
    username = session['username']

    target_wallet = Wallets.query.\
        filter(Wallets.username == username).\
        filter(Wallets.type != 'mining').\
        filter(Wallets.id == wallet_id).first()

    if target_wallet is None:
        return response(error_code=1000)

    db.session.delete(target_wallet)
    db.session.commit()
    return response()


@wallet_blueprint.route('/user/wallet/<coin_name>', methods=['GET'])
@login_required
def get_wallet_by_coin_name(coin_name):
    username = session['username']

    wallets = Wallets.query.filter(Wallets.username == username).filter(Wallets.coin_name == coin_name).all()
    to_json = [wallet.to_json() for wallet in wallets]
    return response(to_json)


@wallet_blueprint.route('/user/wallets', methods=['GET'])
@login_required
def get_wallets():
    username = session['username']
    wallets = Wallets.query.filter(Wallets.username == username).all()
    return response(result=[wallet.to_json() for wallet in wallets])


@wallet_blueprint.route('/user/wallet/payouts', methods=['GET'])
@login_required
def get_payouts():
    if request.args.get('page') is None:
        page = 1
    else:
        page = int(request.args.get('page'))

    username = session['username']
    results = []
    my_payouts = Transactions.query.filter(Transactions.username == username).\
        order_by(Transactions.timestamp.desc()).paginate(page, COUNT_PER_PAGE, error_out=False)

    if my_payouts is not None:
        for item in my_payouts.items:
            results.append(item.to_json())

        return response({'transactions': results, 'hasNext': my_payouts.has_next})

    return response(error_code=1007)


@wallet_blueprint.route('/user/wallet/payouts', methods=['POST'])
@login_required
def payouts():
    username = session['username']
    body = simplejson.loads(request.data)

    authenticate_method = body['authenticate_method']
    authenticate_code = body['authenticate_code']

    if not check_two_factor_authentication(username, authenticate_method, authenticate_code):
        return response(error_code=1012)

    if not check_wallet_form_validation(body) or 'amount' not in body:
        return response(error_code=1000)

    coin_name = body['coin_name']
    coin_name = coin_name.lower().replace(' ', '-')
    address = body['address']

    coin = querys.get_coin_with_coin_name(coin_name)
    wallet = Wallets.query.filter(Wallets.username == username).\
        filter(Wallets.coin_name == coin_name).filter(Wallets.type == 'mining').first()
    if wallet is None or coin is None:
        return response(error_code=1000)

    # Request Amount Check
    amount = float(body['amount'])
    request_amount = float(body['amount']) + coin.tx_fee
    if request_amount > wallet.balance or amount == 0:
        return response(error_code=1000)

    # TODO: 모아서 한번에 보내기? 일단은 한건씩
    tx_result = simplejson.loads(send(os.getenv("RPC_HOST"), coin.port, 0, 'web.payout', [address, amount, username, os.getenv("PAYOUT")]))

    if tx_result['error'] is not None:
        return response(error_code=1017)

    return response({'transactionId': tx_result['result']})


@wallet_blueprint.route('/user/wallet/verify', methods=['GET'])
@login_required
def send_wallet_change_verify_wallet():
    username = session['username']

    _already_send = EmailVerify.query.filter(EmailVerify.username == username).first()
    if _already_send is not None:
        total_seconds = (datetime.utcnow() - _already_send.created).total_seconds()
        if total_seconds < 600:
            return response(error_code=1013)

    _user = g.user

    verify_code = send_account_change_email(_user.email, _user.username, 'Wallet Add or Edit')

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

        return response()

    return response(error_code=1014)
