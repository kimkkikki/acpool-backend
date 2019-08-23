from main import app
from acpool.models import db, Coins
from acpool.rpc.handler import send
import os

with app.app_context():
    coins = db.session.query(Coins).filter(Coins.open.is_(True)).all()

    for coin in coins:
        try:
            send(os.getenv("RPC_HOST"), coin.port, 0, 'web.status', [])
            mining_status = True
        except ConnectionRefusedError:
            mining_status = False

        coin.mining_status = mining_status

    db.session.commit()
