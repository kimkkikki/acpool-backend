from acpool.models import Coins, Users, Block, db, Shares
from sqlalchemy import func
from common.cache import cache
from datetime import datetime, timedelta


def get_open_coins() -> [Coins]:
    cache_key = 'open_coins'
    coins = cache.get('open_coins')
    if coins is None:
        coins = Coins.query.filter(Coins.open.is_(True)).all()
        cache.set(cache_key, coins, timeout=60)

    return coins


def get_coin_with_coin_name(coin_name) -> Coins:
    cache_key = 'coin:' + coin_name
    coin = cache.get(cache_key)

    if coin is None:
        coin = Coins.query.filter(Coins.name == coin_name).first()
        cache.set(cache_key, coin, timeout=600)

    return coin


def get_address_user(address) -> Users:
    cache_key = 'user:' + address
    _user = cache.get(cache_key)

    if _user is None:
        _user = Users.query.filter(Users.username == address).filter(Users.state == 'addressAccount').first()
        cache.set(cache_key, _user, timeout=600)

    return _user


def get_block_history_by_paging(coin_name, page, count_per_page):
    cache_key = 'block_history:%s:%s' % (coin_name, page)
    history = cache.get(cache_key)

    if history is None:
        history = Block.query. \
            filter(Block.coin_name == coin_name). \
            filter(Block.mined.is_(True)). \
            order_by(Block.timestamp.desc()).paginate(page, count_per_page, error_out=False)
        cache.set(cache_key, history, timeout=60)

    return history


def get_last_ten_minute_pool_accepted_shares(coin_name):
    cache_key = 'last_accepted_shares:%s' % coin_name
    shares = cache.get(cache_key)

    if shares is None:
        shares = db.session.query(func.sum(Shares.pool_difficulty)).filter(Shares.coin_name == coin_name) \
            .filter(Shares.pool_result.is_(True)) \
            .filter(Shares.timestamp > (datetime.utcnow() - timedelta(minutes=10))).all()
        cache.set(cache_key, shares, timeout=60)

    return shares
