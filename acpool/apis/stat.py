from flask import Blueprint, session, request
from common.acpool_response import response
from common.decorator import login_required, cached
from acpool.models import Block, db, Shares, Workers, Rewards, Wallets, ShareStats, Transactions
from sqlalchemy import func, distinct
from datetime import datetime, timedelta
from common import utils
from acpool import querys

stat_blueprint = Blueprint('stat_blueprint', __name__)
COUNT_PER_PAGE = 25


@stat_blueprint.route('/stat/<coin_name>/info', methods=['GET'])
@cached(timeout=60)
def pool_dashboard_info(coin_name):
    coin = querys.get_coin_with_coin_name(coin_name)

    last_block_info = Block.query. \
        filter(Block.coin_name == coin_name). \
        order_by(Block.height.desc()).first()
    last_mined_time = db.session.query(Block.timestamp). \
        filter(Block.coin_name == coin_name). \
        filter(Block.mined.is_(True)). \
        order_by(Block.height.desc()).first()
    active_workers = db.session.query(Workers.username, Workers.name). \
        filter(Workers.coin_name == coin_name). \
        filter(Workers.disconnected.is_(None)). \
        group_by(Workers.username, Workers.name).all()

    # shares = querys.get_last_ten_minute_pool_accepted_shares(coin_name)
    # if shares[0][0] is not None:
    hashrate = utils.convert_hashrate_by_share(coin.algorithm, coin.pool_hash)
    if 'equihash' in coin.algorithm:
        pool_hash = utils.hashrate_to_readable_string(hashrate, 'equihash')
    else:
        pool_hash = utils.hashrate_to_readable_string(hashrate)
    # else:
    #     pool_hash = '0 H/s'

    active_users = set()
    for item in active_workers:
        active_users.add(item[0])

    result = {'poolHashRate': pool_hash, 'activeUsers': len(active_users), 'activeWorkers': len(active_workers)}

    if last_block_info is not None:
        result['lastBlockInfo'] = last_block_info.to_json()
    else:
        result['lastBlockInfo'] = Block().to_json()

    if last_mined_time is not None:
        result['lastMinedTime'] = last_mined_time[0]

    return response(result)


@stat_blueprint.route('/stat/<coin_name>/chart', methods=['GET'])
@cached(timeout=10)
def pool_dashboard_chart(coin_name):
    start, end = utils.get_chart_start_end_datetime()
    coin = querys.get_coin_with_coin_name(coin_name)

    pool_graph_datas = db.session.query(func.sum(ShareStats.sum_share_difficulty),
                                        func.sum(ShareStats.accepted_share_count),
                                        func.sum(ShareStats.rejected_share_count),
                                        ShareStats.timestamp). \
        filter(ShareStats.coin_name == coin_name). \
        filter(ShareStats.timestamp >= start). \
        filter(ShareStats.timestamp <= end). \
        group_by(ShareStats.timestamp). \
        order_by(ShareStats.timestamp).all()

    hashrates = []
    shares = []
    for share_stat in pool_graph_datas:
        hashrate = utils.convert_hashrate_by_share(coin.algorithm, share_stat[0])

        date = share_stat[3].strftime('%Y%m%dT%H%M%SZ')
        accepted = share_stat[1]
        rejected = share_stat[2]
        hashrates.append({'date': date, 'pool': hashrate})
        shares.append({'date': date, 'accepted': accepted, 'rejected': rejected})

    result = {
        'hashrates': hashrates,
        'shares': shares,
    }

    return response(result)


@stat_blueprint.route('/stat/<coin_name>/blocks', methods=['GET'])
def block_history(coin_name):
    if request.args.get('page') is None:
        page = 1
    else:
        page = int(request.args.get('page'))

    history = querys.get_block_history_by_paging(coin_name, page, COUNT_PER_PAGE)
    coin = querys.get_coin_with_coin_name(coin_name)
    need_confirmations = coin.confirmation_count

    if history is not None:
        results = []
        for found_block in history.items:
            date = found_block.timestamp

            confirmations = found_block.confirmations
            if confirmations >= need_confirmations:
                confirm_message = 'confirmed'
            elif confirmations == -1:
                confirm_message = 'orphan'
            else:
                confirm_message = str(need_confirmations - confirmations) + ' left'
            result = {
                'block': found_block.height,
                'valid': confirm_message,
                'difficulty': found_block.difficulty,
                'reward': found_block.reward,
                'date': date.strftime("%Y-%m-%d %H:%M")
            }
            results.append(result)
        return response({'rewards': results, 'hasNext': history.has_next})
    else:
        return response(error_code=1007)


def create_my_stat(coin_name, username):
    yesterday = datetime.utcnow() - timedelta(days=1)
    yesterday.replace(second=0, microsecond=0, minute=(yesterday.minute - (yesterday.minute % 10)))

    my_active_workers = db.session.query(distinct(Workers.name)). \
        filter(Workers.coin_name == coin_name). \
        filter(Workers.username == username). \
        filter(Workers.disconnected.is_(None)).count()
    my_rewards = db.session.query(Rewards, Block).join(Block).\
        filter(Rewards.username == username).\
        filter(Block.coin_name == coin_name).all()
    coin = querys.get_coin_with_coin_name(coin_name)

    result_my_rewards = {'confirmed': 0, 'unConfirmed': 0, 'yesterdayEarning': 0}

    if my_rewards is not None:
        for reward in my_rewards:
            confirmations = reward.Block.confirmations
            need_confirmations = coin.confirmation_count
            if confirmations >= need_confirmations:
                result_my_rewards['confirmed'] += round(reward.Rewards.reward, 8)
                if reward.Rewards.timestamp.strftime("%d/%m/%y") == yesterday.strftime("%d/%m/%y"):
                    result_my_rewards['yesterdayEarning'] += round(reward.Rewards.reward, 8)
            else:
                result_my_rewards['unConfirmed'] += round(reward.Rewards.reward, 8)

    ten_minute_ago = datetime.utcnow() - timedelta(minutes=10)
    shares = db.session.query(func.sum(Shares.pool_difficulty)). \
        filter(Shares.coin_name == coin_name).filter(Shares.pool_result.is_(True)). \
        filter(Shares.timestamp > ten_minute_ago).filter(Shares.username == username).all()

    my_hashrate = 0.0
    if shares[0][0] is not None:
        my_hashrate = utils.convert_hashrate_by_share(coin.algorithm, shares[0][0])

    my_wallet = db.session.query(Wallets).\
        filter(Wallets.username == username).\
        filter(Wallets.coin_name == coin_name).\
        filter(Wallets.type == 'mining').\
        first()

    my_balance = 0
    if my_wallet is not None:
        my_balance = my_wallet.balance

    result = {'myHashRate': my_hashrate, 'myActiveWorkers': my_active_workers, 'myRewards': result_my_rewards, 'myBalance': my_balance}

    return result


@stat_blueprint.route('/myStat/<coin_name>/info', methods=['GET'])
@login_required
def my_dashboard_info(coin_name):
    username = session['username']
    result = create_my_stat(coin_name, username)
    return response(result)


@stat_blueprint.route('/myStat/<coin_name>/info/<address>', methods=['GET'])
def address_dashboard_info(coin_name, address):
    address_user = querys.get_address_user(address)
    if address_user is not None:
        result = create_my_stat(coin_name, address)
        return response(result)
    else:
        return response(error_code=1018)


def create_dashboard_chart(coin_name, username):
    start, end = utils.get_chart_start_end_datetime()
    coin = querys.get_coin_with_coin_name(coin_name)

    my_graph_datas = db.session.query(ShareStats). \
        filter(ShareStats.username == username). \
        filter(ShareStats.coin_name == coin_name). \
        filter(ShareStats.timestamp >= start). \
        filter(ShareStats.timestamp <= end). \
        order_by(ShareStats.timestamp).all()

    keys = []
    hashrates = []
    for share_stat in my_graph_datas:
        hashrate = utils.convert_hashrate_by_share(coin.algorithm, share_stat.sum_share_difficulty)
        date = share_stat.timestamp.strftime('%Y%m%dT%H%M%SZ')

        if date in keys:
            index = keys.index(date)
            hashrates[index][share_stat.worker] = hashrate
        else:
            keys.append(date)
            hashrates.append({'date': date, share_stat.worker: hashrate})

    for result in hashrates:
        total = 0
        for key, value in result.items():
            if key != 'date':
                total += result[key]
        result['total'] = total

    date_flag = None
    accepted = 0
    rejected = 0
    shares = []
    for share_stat in my_graph_datas:
        if date_flag is None:
            date_flag = share_stat.timestamp

        if share_stat.timestamp != date_flag:
            date = date_flag.strftime('%Y%m%dT%H%M%SZ')
            shares.append({'date': date, 'accepted': accepted, 'rejected': rejected})
            date_flag = share_stat.timestamp
            accepted = 0
            rejected = 0
        accepted += share_stat.accepted_share_count
        rejected += share_stat.rejected_share_count

    if date_flag is not None:
        date = date_flag.strftime('%Y%m%dT%H%M%SZ')
        shares.append({'date': date, 'accepted': accepted, 'rejected': rejected})

    result = {
        'hashrates': hashrates,
        'shares': shares,
    }

    return result


@stat_blueprint.route('/myStat/<coin_name>/chart', methods=['GET'])
@login_required
def my_dashboard_chart(coin_name):
    username = session['username']
    result = create_dashboard_chart(coin_name, username)
    return response(result)


@stat_blueprint.route('/myStat/<coin_name>/chart/<address>', methods=['GET'])
def address_dashboard_chart(coin_name, address):
    address_user = querys.get_address_user(address)
    if address_user is not None:
        result = create_dashboard_chart(coin_name, address)
        return response(result)
    else:
        return response(error_code=1018)


def create_reward_history(coin_name, username):
    page = int(request.args.get('page'))

    history = db.session.query(Rewards, Block).join(Block).\
        filter(Rewards.username == username).\
        filter(Block.coin_name == coin_name).\
        order_by(Rewards.timestamp.desc()).paginate(page, COUNT_PER_PAGE, error_out=False)

    if history is not None:
        results = []
        for item in history.items:
            found_block = item.Block
            date = found_block.timestamp

            confirmations = found_block.confirmations
            need_confirmations = found_block.coin.confirmation_count
            if confirmations >= need_confirmations:
                confirm_message = 'confirmed'
            elif confirmations == -1:
                confirm_message = 'orphan'
            else:
                confirm_message = str(need_confirmations - confirmations) + ' left'
            result = {
                'block': found_block.height,
                'valid': confirm_message,
                'difficulty': found_block.difficulty,
                'reward': found_block.reward,
                'your_reward': item.Rewards.reward,
                'date': date.strftime("%Y-%m-%d %H:%M")
            }
            results.append(result)
        return response({'rewards': results, 'hasNext': history.has_next})
    else:
        return response(error_code=1007)


@stat_blueprint.route('/myStat/<coin_name>/rewards', methods=['GET'])
@login_required
def my_reward_history(coin_name):
    username = session['username']
    return create_reward_history(coin_name, username)


@stat_blueprint.route('/myStat/<coin_name>/rewards/<address>', methods=['GET'])
def address_reward_history(coin_name, address):
    address_user = querys.get_address_user(address)
    if address_user is not None:
        return create_reward_history(coin_name, address)
    else:
        return response(error_code=1018)


def create_reward_chart(coin_name, username):
    one_month_ago = datetime.utcnow().replace(minute=0, hour=0, second=0, microsecond=0) - timedelta(days=30)

    # coin = querys.get_coin_with_coin_name(coin_name)
    my_rewards = db.session.query(func.sum(Rewards.reward), func.date_trunc('day', Rewards.timestamp).label('day')). \
        join(Block). \
        filter(Rewards.username == username). \
        filter(Block.coin_name == coin_name). \
        filter(Rewards.timestamp >= one_month_ago). \
        group_by('day').order_by('day').all()

    results = []
    for my_reward in my_rewards:
        results.append({'reward': my_reward[0], 'day': my_reward[1].strftime('%Y%m%d')})

    return results


@stat_blueprint.route('/myStat/<coin_name>/rewards/chart', methods=['GET'])
@login_required
def my_reward_chart(coin_name):
    username = session['username']
    results = create_reward_chart(coin_name, username)
    return response(results)


@stat_blueprint.route('/myStat/<coin_name>/rewards/chart/<address>', methods=['GET'])
def address_reward_chart(coin_name, address):
    address_user = querys.get_address_user(address)
    if address_user is not None:
        results = create_reward_chart(coin_name, address)
        return response(results)
    else:
        return response(error_code=1018)


@stat_blueprint.route('/myStat/<coin_name>/payouts/<address>', methods=['GET'])
def get_address_payouts(coin_name, address):
    if request.args.get('page') is None:
        page = 1
    else:
        page = int(request.args.get('page'))

    results = []
    address_user = querys.get_address_user(address)
    if address_user is not None:
        my_payouts = Transactions.query.\
            filter(Transactions.username == address).\
            filter(Transactions.coin_name == coin_name).\
            order_by(Transactions.timestamp.desc()).paginate(page, COUNT_PER_PAGE, error_out=False)

        if my_payouts is not None:
            for item in my_payouts.items:
                results.append(item.to_json())

            return response({'transactions': results, 'hasNext': my_payouts.has_next})
        return response(error_code=1007)

    else:
        return response(error_code=1018)
