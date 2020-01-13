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
    stock_id = db.Column(db.Integer, db.ForeignKey("stocks.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.Text, nullable=False, default="USD")
    stock = relationship(Stock)