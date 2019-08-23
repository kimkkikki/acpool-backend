from dotenv import load_dotenv
from flask import Flask
from acpool import models
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_cors import CORS
from acpool.apis.user import user_blueprint
from acpool.apis.stat import stat_blueprint
from acpool.apis.wallet import wallet_blueprint
from acpool.apis.home import home_blueprint
from acpool.apis.comments import comments_blueprint
from acpool.schedule.update_price import scheduler
import atexit
import os

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY")

postgresql_uri = 'postgresql://{}:{}@{}:{}/simple_mining'.format(os.getenv("POSTGRESQL_USER"), os.getenv("POSTGRESQL_PASSWORD"), os.getenv("POSTGRESQL_URL"),
                                                                 os.getenv("POSTGRESQL_PORT"))
app.config['SQLALCHEMY_DATABASE_URI'] = postgresql_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
models.db.init_app(app)

migrate = Migrate(app, models.db)

if os.getenv("DEBUG") == 'true':
    admin = Admin(app, name='acpool', template_mode='bootstrap3')
    admin.add_view(ModelView(models.Coins, models.db.session))

    class UsernameAndEmailModelView(ModelView):
        column_searchable_list = ('username', 'email')

    admin.add_view(UsernameAndEmailModelView(models.Users, models.db.session))

    class UsernameAndCoinNameModelView(ModelView):
        column_searchable_list = ('username', 'coin_name')

    admin.add_view(UsernameAndCoinNameModelView(models.Wallets, models.db.session))
    admin.add_view(UsernameAndCoinNameModelView(models.Transactions, models.db.session))
    admin.add_view(UsernameAndCoinNameModelView(models.Workers, models.db.session))
    admin.add_view(UsernameAndCoinNameModelView(models.Shares, models.db.session))
    admin.add_view(UsernameAndCoinNameModelView(models.Block, models.db.session))
    admin.add_view(UsernameAndCoinNameModelView(models.ShareStats, models.db.session))

    class UsernameModelView(ModelView):
        column_searchable_list = ['username']

    admin.add_view(UsernameModelView(models.Rewards, models.db.session))
    admin.add_view(UsernameModelView(models.EmailVerify, models.db.session))

    admin.add_view(ModelView(models.Operations, models.db.session))

app.register_blueprint(user_blueprint, url_prefix='/api')
app.register_blueprint(stat_blueprint, url_prefix='/api')
app.register_blueprint(wallet_blueprint, url_prefix='/api')
app.register_blueprint(home_blueprint, url_prefix='/api')
app.register_blueprint(comments_blueprint, url_prefix='/api')

with app.app_context():
    if not os.getenv("DEBUG") == 'true':
        scheduler.app = app
        scheduler.start()

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    if os.getenv("DEBUG") == 'true':
        app.run(debug=True)
    else:
        app.run(debug=False, host='0.0.0.0')
