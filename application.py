import os
import requests

# from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from models import *

from helpers import apology, login_required, lookup, usd

# configure application
app = Flask(__name__)

# ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
# db = SQL("sqlite:///finance.db")

# configure DB to interact with Flask
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# initialize app
print("INITIALIZE")
# https://stackoverflow.com/questions/9692962/flask-sqlalchemy-import-context-issue/9695045#9695045
db.init_app(app)
# push the context so that DB operations are performed inside an application context
app.app_context().push()
# get models & create corresponding DB tables if necessary
db.create_all()

# make sure API key is set
if os.environ.get("API_KEY"):
    api_token = os.environ.get("API_KEY")
    api_url_base = "https://cloud.iexapis.com/stable/stock/"
    api_url_suffix = "/quote?token=" + api_token
else:
    raise RuntimeError("API_KEY not set")

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    print("INDEX")

    return render_template("index.html")

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """
    Get stock quote.

    example of API call:
    https://cloud.iexapis.com/stable/stock/aapl/quote?token=API_TOKEN
    """
    print("QUOTE")

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # consume the API to get the latest price
        data = lookup(request.form.get("stock"))
        # format the amount in USD
        amount = usd(data["price"])

        return render_template("quote_response.html", stock=data["symbol"], name=data["name"], amount=amount)
    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote_request.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    print("BUY")

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        pass
    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    print("SELL")

    return apology("TODO")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    print("HISTORY")

    return apology("TODO")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    print("LOGIN")

    # forget any user_id
    session.clear()

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # query database for username using SQLAlchemy
        user = User.query.filter_by(username=request.form.get("username")).first()

        # ensure username exists and password is correct
        if user is None or not check_password_hash(user.hash, request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # remember which user has logged in
        session["user_id"] = user.id

        # redirect user to home page
        return redirect("/")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    print("LOGOUT")

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    print("REGISTER")

    # forget any user_id
    session.clear()

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # query database for username using SQLAlchemy
        user_exists = User.query.filter_by(username=request.form.get("username")).count()

        # ensure username does not exist
        if user_exists == 1:
            return apology("username already exists", 403)

        # ensure username is at least 3 characters long
        if len(request.form.get("username")) < 3:
            return apology("username must be at least 3 characters long", 403)

        # ensure password is correct
        if request.form.get("password") != request.form.get("password-confirm") :
            return apology("passwords must be identical", 403)

        # create the user based on the model provided
        user = User(username=request.form.get("username"),hash=generate_password_hash(request.form.get("password")))
        # add the user to generate an Id
        db.session.add(user)
        # commit changes
        db.session.commit()
        # retrieve the Id by querying the DB once again
        user = User.query.filter_by(username=request.form.get("username")).first()

        # remember which user has logged in
        if user is not None:
            session["user_id"] = user.id
            # redirect user to home page
            return redirect("/")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
