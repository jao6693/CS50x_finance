from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class User(db.Model):
    """Master Data Table for Users"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    hash = db.Column(db.Text, nullable=False)
    cash = db.Column(db.Float, nullable=False, default=10000.00)

    # additional methods to access User model
    @staticmethod
    def create(username, hash):
        user_db = User(username=username,hash=hash)
        # add the user to the DB
        db.session.add(user_db)
        # commit changes
        db.session.commit()
        # return the newly created user
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_by_id(user_id):
        return User.query.get(user_id)

    @staticmethod
    def get_by_username(username):
        return User.query.filter_by(username=username).first()

    @staticmethod
    def exist_by_username(username):
        """User existence check using username"""
        exist = User.query.filter_by(username=username).count()
        if exist == 0:
            return False
        else:
            return True

class Stock(db.Model):
    """Master Data Table for Stocks"""
    __tablename__ = "stocks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    stock = db.Column(db.Text, nullable=False)
    name = db.Column(db.String(50), nullable=False)

    # additional methods to acces Stock model
    @staticmethod
    def get_all(user_id):
        # user_id is always used to restrict selection
        return db.session.query(Stock.id.label("stock_id"), Stock.stock, Stock.name, \
            db.func.sum(Transaction.quantity).label("quantity"), db.func.sum(Transaction.amount).label("amount")) \
            .filter(Transaction.stock_id == Stock.id, Transaction.user_id == user_id) \
            .group_by("stock_id", "stock", "name") \
            .order_by("stock") \
            .all()

    @staticmethod
    def get_by_name(name):
        return Stock.query.filter_by(name=name).first()

    @staticmethod
    def exist_by_name(name):
        """User existence check using username"""
        exist = Stock.query.filter_by(name=name).count()
        if exist == 0:
            return False
        else:
            return True

class Transaction(db.Model):
    """Transactional Table for Stock Inventory"""
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_on = db.Column(db.DateTime, server_default=db.func.now())
    stock_id = db.Column(db.Integer, db.ForeignKey("stocks.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Float, nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.Text, nullable=False, default="USD")
    visible = db.Column(db.Boolean, nullable=True, default=True)

    stock = relationship(Stock)

    # additional methods to access Transaction model
    @staticmethod
    def create(user_id, amount, visible):
        transaction_db = Transaction(user_id=user_id, amount=amount, visible=visible)
        # add the transaction to the DB
        db.session.add(transaction_db)
        # commit changes
        db.session.commit()
        # return parameter
        return True

    @staticmethod
    def get_all(user_id):
        """Transactions per user"""
        # user_id is always used to restrict selection
        return db.session.query(Stock.id, Stock.stock, Stock.name, \
            Transaction.quantity, Transaction.price, Transaction.created_on) \
            .filter(Transaction.stock_id == Stock.id, Transaction.user_id == user_id) \
            .order_by("created_on") \
            .all()

    @staticmethod
    def get_by_symbol(user_id, symbol):
        """Transaction per symbol"""
        return db.session.query(Stock.id, Stock.stock, Stock.name, \
            db.func.sum(Transaction.quantity).label("quantity"), db.func.sum(Transaction.amount).label("amount")) \
            .filter(Transaction.stock_id == Stock.id, Stock.stock == symbol, Transaction.user_id == user_id) \
            .group_by("stock_id") \
            .first()
