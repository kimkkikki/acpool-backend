import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref
from libgravatar import Gravatar

db = SQLAlchemy()


class Coins(db.Model):
    __tablename__ = 'coins'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, unique=True, nullable=False)
    code = db.Column(db.String)
    algorithm = db.Column(db.String, nullable=False)
    port = db.Column(db.Integer, nullable=False)
    pool_hash = db.Column(db.Float, default=0)
    usd_price = db.Column(db.Float, default=0)
    btc_price = db.Column(db.Float, default=0)
    confirmation_count = db.Column(db.Integer)
    pool_address = db.Column(db.String)
    shield_address = db.Column(db.String)
    fee = db.Column(db.Float, default=2.0)
    tx_fee = db.Column(db.Float, default=0.0001)
    open = db.Column(db.Boolean, default=True, index=True)
    mining_status = db.Column(db.Boolean, default=True)

    def __str__(self):
        return self.name

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'algorithm': self.algorithm,
            'port': self.port,
            'pool_hash': self.pool_hash,
            'btcPrice': self.btc_price,
            'usdPrice': self.usd_price,
            'fee': self.fee,
            'price': self.price,
            'confirmation_count': self.confirmation_count
        }


class ShareStats(db.Model):
    __tablename__ = 'share_stat'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    coin_name = db.Column(db.String, db.ForeignKey('coins.name'), index=True)
    coin = db.relationship("Coins")
    username = db.Column(db.String, db.ForeignKey('users.username'), index=True)
    user = db.relationship("Users")
    worker = db.Column(db.String)
    sum_share_difficulty = db.Column(db.Float)
    accepted_share_count = db.Column(db.Integer)
    rejected_share_count = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)

    def __str__(self):
        return '<ShareStats id: %s, coin_name: %s, username: %s, worker: %s, sum_share_difficulty: %s' \
               ', share_count: %s, timestamp: %s>' % \
               (self.id, self.coin_name, self.username, self.worker, self.sum_share_difficulty,
                self.share_count, self.timestamp)

    def to_json(self):
        return {
            'id': self.id,
            'coin': self.coin_name,
            'username': self.username,
            'worker': self.worker,
            'sum_share_difficulty': self.sum_share_difficulty,
            'share_count': self.share_count,
            'timestamp': None if self.timestamp is None else self.timestamp.strftime('%Y%m%dT%H%M%S%z'),
        }


class Shares(db.Model):
    __tablename__ = 'shares'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    coin_name = db.Column(db.String, db.ForeignKey('coins.name'), index=True)
    coin = db.relationship("Coins")
    username = db.Column(db.String, db.ForeignKey('users.username'), index=True)
    user = db.relationship("Users")
    worker = db.Column(db.String)
    pool_result = db.Column(db.Boolean, index=True)
    share_result = db.Column(db.Boolean)
    block_height = db.Column(db.Integer, index=True)
    share_difficulty = db.Column(db.Float)
    pool_difficulty = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)

    def __str__(self):
        return '<Share id: %s, coin_name: %s, username: %s, worker: %s, pool_difficulty: %s' \
               ', pool_result: %r,' \
               ' share_result: %r, height: %s, share_diff: %s, timestamp: %s>' % \
               (self.id, self.coin_name, self.username, self.worker, self.pool_difficulty,
                self.pool_result, self.share_result, self.block_height, self.share_difficulty, self.timestamp)

    def to_json(self):
        return {
            'id': self.id,
            'coin': self.coin_name,
            'username': self.username,
            'worker': self.worker,
            'pool_result': self.pool_result,
            'share_result': self.share_result,
            'block_height': self.block_height,
            'share_difficulty': self.share_difficulty,
            'pool_difficulty': self.pool_difficulty,
            'timestamp': None if self.timestamp is None else self.timestamp.strftime('%Y%m%dT%H%M%S%z'),
        }


class Block(db.Model):
    __tablename__ = 'block'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    coin_name = db.Column(db.String, db.ForeignKey('coins.name'), index=True)
    coin = db.relationship("Coins")
    height = db.Column(db.Integer, index=True)
    difficulty = db.Column(db.Float)
    net_hashrate = db.Column(db.Float)
    reward = db.Column(db.Float)
    mined = db.Column(db.Boolean, default=False, index=True)
    hash = db.Column(db.String)
    confirmations = db.Column(db.Integer, index=True)
    username = db.Column(db.String, db.ForeignKey('users.username'))
    user = db.relationship("Users")
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)

    def __str__(self):
        return '<Block id: %s, coin_name: %s, height: %s, difficulty: %s, net_hashrate: %s, reward: %s, mined: %s, timestamp: %s>' % \
               (self.id, self.coin_name, self.height, self.difficulty, self.net_hashrate, self.reward, self.mined, self.timestamp)

    def to_json(self):
        return {
            'id': self.id,
            'coin_name': self.coin_name,
            'height': self.height,
            'difficulty': self.difficulty,
            'net_hashrate': self.net_hashrate,
            'reward': self.reward,
            'mined': self.mined,
            'confirmations': self.confirmations,
            'username': self.username,
            'timestamp': None if self.timestamp is None else self.timestamp.strftime('%Y%m%dT%H%M%S%z'),
        }


class Rewards(db.Model):
    __tablename__ = 'rewards'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, db.ForeignKey('users.username'), index=True)
    user = db.relationship("Users")
    block_id = db.Column(db.Integer, db.ForeignKey('block.id'), index=True)
    block = db.relationship("Block", backref='rewards')
    contribution = db.Column(db.Float)
    reward = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    def __str__(self):
        return '<Rewards id: %s, username: %s, block_id: %s, contribution: %s, reward: %s, timestamp: %s>' % \
               (self.id, self.username, self.block_id, self.contribution, self.reward, self.timestamp)

    def to_json(self):
        return {
            'id': self.id,
            'username': self.usernamecoin,
            'block_id': self.block_id,
            'contribution': self.contribution,
            'reward': self.reward,
            'timestamp': None if self.timestamp is None else self.timestamp.strftime('%Y%m%dT%H%M%S%z'),
        }


class Operations(db.Model):
    __tablename__ = 'operations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    op_id = db.Column(db.String, nullable=False, unique=True, index=True)
    coin_name = db.Column(db.String, db.ForeignKey('coins.name'), index=True)
    coin = db.relationship("Coins")
    tx_id = db.Column(db.String)
    status = db.Column(db.String, default='executing', index=True)
    method = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    def __str__(self):
        return self.op_id


class Transactions(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    op_id = db.Column(db.String, db.ForeignKey('operations.op_id'), index=True)
    operation = db.relationship("Operations")
    tx_id = db.Column(db.String, index=True)
    coin_name = db.Column(db.String, db.ForeignKey('coins.name'), index=True)
    coin = db.relationship("Coins")
    username = db.Column(db.String, db.ForeignKey('users.username'), index=True)
    user = db.relationship("Users")
    block_hash = db.Column(db.String)
    type = db.Column(db.String, default='auto')
    from_address = db.Column(db.String, index=True, nullable=False)
    to_address = db.Column(db.String, index=True, nullable=False)
    amount = db.Column(db.Float)
    fee = db.Column(db.Float)
    confirmations = db.Column(db.Integer, default=0, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    def __str__(self):
        return self.tx_id

    def to_json(self):
        return {
            'id': self.id,
            'op_id': self.op_id,
            'tx_id': self.tx_id,
            'coin_name': self.coin_name,
            'username': self.username,
            'block_hash': self.block_hash,
            'type': self.type,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'amount': self.amount,
            'fee': self.fee,
            'confirmations': self.confirmations,
            'timestamp': None if self.timestamp is None else self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        }


class Wallets(db.Model):
    __tablename__ = 'wallets'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, db.ForeignKey('users.username'), index=True)
    user = db.relationship("Users", back_populates="wallets")
    coin_name = db.Column(db.String, db.ForeignKey('coins.name'), index=True)
    coin = db.relationship("Coins")
    address = db.Column(db.String, index=True)
    balance = db.Column(db.Float, default=0)
    lock_balance = db.Column(db.Float, default=0, comment='Before transaction completed')
    label = db.Column(db.String)
    type = db.Column(db.String, default='acpool', comment='mining, acpool, other')
    payout = db.Column(db.Float, default=0, comment='0 means no auto payout')
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    def __str__(self):
        return '<Wallets id: %s, username: %s, coin_name: %s, address: %s, balance: %s, timestamp: %s>' % \
               (self.id, self.username, self.coin_name, self.address, self.balance, self.timestamp)

    def to_json(self):
        return {
            'id': self.id,
            'username': self.username,
            'coin_name': self.coin_name,
            'address': self.address,
            'balance': self.balance,
            'lock_balance': self.lock_balance,
            'label': self.label,
            'type': self.type,
            'payout': self.payout,
            'timestamp': None if self.timestamp is None else self.timestamp.strftime('%Y%m%dT%H%M%S%z'),
        }


class Users(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, nullable=False, unique=True, index=True)
    wallets = db.relationship("Wallets", back_populates="user")
    password = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True, index=True)
    state = db.Column(db.String, default='NeedValidateEmail', nullable=False)
    otp_key = db.Column(db.String, nullable=True)
    otp_state = db.Column(db.Boolean, default=False)
    email_notification = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    def __str__(self):
        return self.username

    def to_json(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'state': self.state,
            'otp_key': self.otp_key,
            'otp_state': self.otp_state,
            'emailNotification': self.email_notification,
            'created': self.created,
            'updated': self.updated,
        }


class EmailVerify(db.Model):
    __tablename__ = 'email_verify'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, db.ForeignKey('users.username'), index=True)
    user = db.relationship("Users")
    verify_code = db.Column(db.String(10))
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)


class Workers(db.Model):
    __tablename__ = 'workers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip = db.Column(db.String, nullable=False)
    username = db.Column(db.String, db.ForeignKey('users.username'), index=True)
    user = db.relationship("Users")
    coin_name = db.Column(db.String, db.ForeignKey('coins.name'))
    coin = db.relationship("Coins")
    name = db.Column(db.String, default='default')
    miner = db.Column(db.String)
    connected = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    disconnected = db.Column(db.DateTime, nullable=True, index=True)

    def __str__(self):
        return '<Workers id: %s, ip: %s, username: %s, coin_name: %s, name: %s, miner: %s, connected: %s, disconnected: %s>' % \
               (self.id, self.ip, self.username, self.coin_name, self.name, self.miner, self.connected, self.disconnected)


class Comments(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, db.ForeignKey('users.username'), index=True)
    user = db.relationship("Users")
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    childs = db.relationship("Comments", backref=backref('parent', remote_side=[id]))
    contents = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)

    def __str__(self):
        return '<Comments id: %s, username: %s, parent_id: %s, contents: %s, created: %s>' % \
               (self.id, self.username, self.parent_id, self.contents, self.created)

    def to_json(self):
        gravatar = Gravatar(self.user.email)
        src = gravatar.get_image()
        return {
            'id': self.id,
            'username': self.username,
            'gravatar': src,
            'contents': self.contents,
            'childs': [child.to_json() for child in self.childs],
            'created': None if self.created is None else self.created.strftime('%Y%m%dT%H%M%S%z'),
        }
