from dotenv import load_dotenv
from flask import Flask
from acpool.models import db
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
import os

load_dotenv()

app = Flask(__name__)
postgresql_uri = 'postgresql://{}:{}@{}:{}/simple_mining'.format(os.getenv("POSTGRESQL_USER"), os.getenv("POSTGRESQL_PASSWORD"), os.getenv("POSTGRESQL_URL"),
                                                                 os.getenv("POSTGRESQL_PORT"))
app.config['SQLALCHEMY_DATABASE_URI'] = postgresql_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db.init_app(app)
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
