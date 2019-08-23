from acpool.models import Coins, db
import simplejson
import requests
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()
app = None


def update_coin_price():
    try:
        with scheduler.app.app_context():
            coin_list = simplejson.loads(requests.get('https://api.coinmarketcap.com/v2/listings/').content)
            pool_list = Coins.query.all()

            for pool_coin in pool_list:
                coin_market_cap_id = 0
                for coin in coin_list['data']:
                    if coin['symbol'] == pool_coin.code:
                        coin_market_cap_id = coin['id']
                        break

                if coin_market_cap_id != 0:
                    ticket_url = 'https://api.coinmarketcap.com/v2/ticker/{}/?convert=BTC'.format(coin_market_cap_id)
                    price_data = simplejson.loads(requests.get(ticket_url).content)
                    usd_price = price_data['data']['quotes']['USD']['price']
                    btc_price = price_data['data']['quotes']['BTC']['price']

                    pool_coin.usd_price = usd_price
                    pool_coin.btc_price = btc_price

            db.session.commit()
            logger.info('Price Update Success')
    except Exception as e:
        logger.error('Price Update Failure, {}'.format(e))


scheduler.add_job(func=update_coin_price, trigger=IntervalTrigger(hours=1), id='coin_price_update', name='Update coin price 1hour', replace_existing=True)
