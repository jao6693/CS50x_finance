from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    """Master Data Table for Users"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    hash = db.Column(db.Text, nullable=False)
    cash = db.Column(db.Float, nullable=False, default=10000.00)

class Stock(db.Model):
    """Master Data Table for Stocks"""
    __tablename__ = "stocks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    stock = db.Column(db.Text, nullable=False)
    name = db.Column(db.String(50), nullable=False)

class Transaction(db.Model):
    """Transactional Table for Bought/Sold Stocks"""
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_on = db.Column(db.DateTime, server_default=db.func.now())
    stock_id = db.Column(db.Integer, db.ForeignKey("stock.id"), nullable=False)
    user_id = person_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.Text, nullable=False, default="usd")