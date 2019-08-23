from flask import Blueprint, session
from common.acpool_response import response
from common.decorator import login_required, cached
from acpool.models import Block, db, Shares, Workers, Rewards
from sqlalchemy import func
from datetime import datetime, timedelta
from common import utils
from operator import itemgetter
from acpool import querys

home_blueprint = Blueprint('home', __name__)


@home_blueprint.route('/home/blocks')
@cached(timeout=10)
def mined_blocks():
    coins = querys.get_open_coins()
    mined_block_list = Block.query.filter(Block.mined.is_(True)).order_by(Block.timestamp.desc()).limit(len(coins))

    results = []
    for block in mined_block_list:
        block_json = block.to_json()

        coin_confirmations = 100  # Default 100
        for coin in coins:
            if coin.name == block.coin_name:
                coin_confirmations = coin.confirmation_count
                break

        if block.confirmations >= coin_confirmations:
            block_json['status'] = 'confirmed'
        elif block.confirmations == -1:
            block_json['status'] = 'orphan'
        else:
            block_json['status'] = '%s left' % (coin_confirmations - block.confirmations)

        results.append(block_json)

    return response(results)


@home_blueprint.route('/home/coins', methods=['GET'])
@cached(timeout=60)
def home_coins():
    result_list = []
    coins = querys.get_open_coins()
    all_workers = Workers.query.filter(Workers.disconnected.is_(None)).all()

    for coin in coins:
        hashrate = utils.convert_hashrate_by_share(coin.algorithm, coin.pool_hash)
        if 'equihash' in coin.algorithm:
            pool_hash = utils.hashrate_to_readable_string(hashrate, 'equihash')
        else:
            pool_hash = utils.hashrate_to_readable_string(hashrate)

        worker_count = 0
        for worker in all_workers:
            if worker.coin_name == coin.name:
                worker_count += 1

        result = {
            'name': coin.name,
            'code': coin.code,
            'port': coin.port,
            'algorithm': coin.algorithm,
            'fee': '%s %s' % (coin.fee, '%'),
            'poolHash': pool_hash,
            'activeWorkers': worker_count,
            'transactionFee': coin.tx_fee,
            'btcPrice': coin.btc_price,
            'usdPrice': coin.usd_price,
            'miningStatus': coin.mining_status,
        }
        result_list.append(result)

    result_list = sorted(result_list, key=itemgetter('activeWorkers'), reverse=True)

    return response(result_list)


@home_blueprint.route('/home/my')
@login_required
def my_stat():
    username = session['username']

    # Last 24 Hours Earning coins
    coins = querys.get_open_coins()

    start_date = datetime.now() - timedelta(days=1)
    rewards = Rewards.query.filter(Rewards.username == username).filter(Rewards.timestamp > start_date).all()

    my_earning_coins = []
    earnings = []
    sum_of_unconfirmed_btc = 0
    sum_of_unconfirmed_usd = 0
    sum_of_confirmed_btc = 0
    sum_of_confirmed_usd = 0
    for reward in rewards:
        reward_coin = None
        for coin in coins:
            if coin.name == reward.block.coin_name:
                reward_coin = coin
                break

        if reward_coin is None:
            reward_coin = reward.block.coin

        reward_block = reward.block
        confirmations = reward_block.confirmations
        need_confirmations = reward_coin.confirmation_count
        btc_price = reward_coin.btc_price
        usd_price = reward_coin.usd_price

        if reward.block.coin_name not in my_earning_coins:
            my_earning_coins.append(reward_block.coin_name)
            earnings.append({'coinName': reward_block.coin_name, 'confirmed': 0, 'unconfirmed': 0})
            index = my_earning_coins.index(reward_block.coin_name)
        else:
            index = my_earning_coins.index(reward_block.coin_name)

        coin_result = earnings[index]
        if confirmations >= need_confirmations:
            coin_result['confirmed'] += reward.reward
            sum_of_confirmed_btc += reward.reward * btc_price
            sum_of_confirmed_usd += reward.reward * usd_price
        else:
            coin_result['unconfirmed'] += reward.reward
            sum_of_unconfirmed_btc += reward.reward * btc_price
            sum_of_unconfirmed_usd += reward.reward * usd_price

    if sum_of_confirmed_btc != 0 or sum_of_unconfirmed_btc != 0:
        earnings.append({'coinName': '*bitcoin', 'confirmed': sum_of_confirmed_btc, 'unconfirmed': sum_of_unconfirmed_btc})

    if sum_of_confirmed_usd != 0 or sum_of_unconfirmed_usd != 0:
        earnings.append({'coinName': '*usdt', 'confirmed': sum_of_confirmed_usd, 'unconfirmed': sum_of_unconfirmed_usd})

    for earning in earnings:
        earning['confirmed'] = utils.translate_float_string(round(earning['confirmed'], 8))
        earning['unconfirmed'] = utils.translate_float_string(round(earning['unconfirmed'], 8))

    # Current Workers status
    workers = Workers.query.filter(Workers.username == username).filter(Workers.disconnected.is_(None)).all()

    # 내 Worker가 일하고있는 코인들
    my_working_coins = []
    work_fors = []
    for worker in workers:
        if worker.coin_name in my_working_coins:
            index = my_working_coins.index(worker.coin_name)
        else:
            my_working_coins.append(worker.coin_name)
            work_fors.append({'name': worker.coin_name, 'workers': 0})
            index = my_working_coins.index(worker.coin_name)

        work_for = work_fors[index]
        work_for['workers'] += 1

    # My Hashrate
    ten_minute_ago = datetime.now() - timedelta(minutes=10)
    shares = db.session.query(func.sum(Shares.pool_difficulty)).filter(Shares.pool_result.is_(True)). \
        filter(Shares.timestamp > ten_minute_ago).filter(Shares.username == username).all()

    my_hashrate = 0.0
    if shares[0][0] is not None:
        my_hashrate = shares[0][0] * 7158388.055

    my_stat_result = {'earnings': earnings, 'workers': len(workers), 'workFors': work_fors, 'hashrate': my_hashrate}
    return response(my_stat_result)


@home_blueprint.route('/notice')
def notice():
    pass


@home_blueprint.route('/home/coins/<coin_name>', methods=['GET'])
@cached(timeout=60)
def coin_detail(coin_name):
    coin = querys.get_coin_with_coin_name(coin_name)

    if coin is None:
        return response(error_code=1000)

    # shares = querys.get_last_ten_minute_pool_accepted_shares(coin.name)
    # if shares[0][0] is not None:
    hashrate = utils.convert_hashrate_by_share(coin.algorithm, coin.pool_hash)
    if 'equihash' in coin.algorithm:
        pool_hash = utils.hashrate_to_readable_string(hashrate, 'equihash')
    else:
        pool_hash = utils.hashrate_to_readable_string(hashrate)
    # else:
    #     pool_hash = '0 H/s'

    workers = Workers.query.filter(Workers.coin_name == coin.name).filter(Workers.disconnected.is_(None)).count()

    result = {
        'name': coin.name,
        'code': coin.code,
        'port': coin.port,
        'algorithm': coin.algorithm,
        'fee': '%s %s' % (coin.fee, '%'),
        'poolHash': pool_hash,
        'activeWorkers': workers,
        'transactionFee': coin.tx_fee,
        'miningStatus': coin.mining_status,
        'btcPrice': coin.btc_price,
        'usdPrice': coin.usd_price,
    }
    return response(result)
