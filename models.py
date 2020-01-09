from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, nullable=False)
    hash = db.Column(db.Text, nullable=False)
    cash = db.Column(db.Float, nullable=False, default=10000.00)