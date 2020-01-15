import os
import requests

# from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from models import *
from sqlalchemy import select
from sqlalchemy.sql import func

from helpers import apology, login_required, lookup, usd, percentage

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
# https://cs50.stackexchange.com/questions/34720/pset8-2019-jinja-env-filters-error
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["percentage"] = percentage

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
print("Initializing the Flask application...")
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
    print("Rendering Portfolio View")

    # get current user's balance
    user_db = User.query.get(session["user_id"])

    # get all the stocks currently available
    transactions_db = db.session.query(Stock.stock, Stock.name, db.func.sum(Transaction.quantity).label("quantity"), db.func.sum(Transaction.amount).label("amount")) \
        .filter(Transaction.stock_id == Stock.id, Transaction.user_id == session["user_id"]) \
        .group_by("stock_id").all()

    # lookup for current price/format the amount/calculate the grand total
    grand_total = user_db.cash
    transaction = {}
    transactions = []

    # for transaction_db in transactions_db:
    valid_transactions_db = (transaction_db for transaction_db in transactions_db if transaction_db.quantity > 0)
    for transaction_db in valid_transactions_db:
        transaction["stock"] = transaction_db.stock
        transaction["name"] = transaction_db.name
        transaction["quantity"] = transaction_db.quantity
        # lookup for current price
        api_response = lookup(transaction_db.stock)
        price = float(api_response["price"])
        transaction["price"] = price
        # define a comparison indicator on the price (latest) vs average price (DB)
        avg_price = float(transaction_db.amount / transaction_db.quantity)
        if round(price, 2) > round(avg_price, 2):
            transaction["price_indicator"] = "table-success"
        elif round(price, 2) == round(avg_price, 2):
            transaction["price_indicator"] = "table-secondary"
        else:
            transaction["price_indicator"] = "table-danger"
        # the price variation is calculated based on historical average + latest price
        transaction["variation"] = ((price - avg_price) / avg_price)
        # the amount is valuated based on the latest price
        amount = float(transaction_db.quantity * price)
        transaction["amount"] = amount
        transactions.append(transaction.copy())

        grand_total += amount

    return render_template("index.html", transactions=transactions, cash=user_db.cash, grand_total=grand_total)

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """
    Get stock quote.

    example of API call:
    https://cloud.iexapis.com/stable/stock/aapl/quote?token=API_TOKEN
    """
    print("Rendering Quote View")

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # consume the API to get the latest price
        api_response = lookup(request.form.get("stock"))
        # check for potential errors
        if api_response is None:
            # add an explicit message to the page
            flash("Stock does not exist")
            # go back to quote page
            return render_template("quote_request.html")
        else:
            # format the amount in USD
            amount = api_response["price"]

            return render_template("quote_response.html", stock=api_response["symbol"], name=api_response["name"], amount=amount)
    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote_request.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    print("Rendering Buy View")

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # use a validation indicator
        validated = True
        # consume the API to get the latest price
        api_response = lookup(request.form.get("stock"))
        # check for potential errors
        if api_response is None:
            validated = False
            # add an explicit message to the page
            flash("stock does not exist")
        else:
            # calculate the transaction amount to check whether the user can afford to purchase these stocks
            amount = int(request.form.get("quantity")) * float(api_response["price"])
            # query the DB to get the cash available for the user
            user_db = User.query.get(session["user_id"])
            if user_db.cash < amount:
                validated = False
                # add an explicit message to the page
                flash("balance too low")
            else:
                # update the transaction & the stock tables
                stock_db_exists = Stock.query.filter_by(name=api_response["name"]).count()

                if stock_db_exists == 0:
                    stock_db = Stock(stock=api_response["symbol"], name=api_response["name"])
                    # add the stock to the master data
                    db.session.add(stock_db)
                    # commit changes to get an Id for the stock
                    db.session.commit()

                stock_db = Stock.query.filter_by(name=api_response["name"]).first()
                # add the transaction to the transaction data
                transaction_db = Transaction(stock_id=stock_db.id, user_id=session["user_id"], \
                    quantity=int(request.form.get("quantity")), price=float(api_response["price"]), amount=amount)
                # post the transaction data
                db.session.add(transaction_db)
                # subtract the amount of the transaction to the user's cash
                user_db.cash -= amount
                # commit changes to validate the transaction
                db.session.commit()

                # add an explicit message to the page
                flash("Bought!")
                # redirect user to home page
                return redirect("/")

        if validated == False:
            # go back to buy page
            return render_template("buy.html")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    print("Rendering Sell View")

    # get all the stocks currently available
    stocks_db = db.session.query(Stock.id, Stock.stock, db.func.sum(Transaction.quantity).label("quantity")) \
        .filter(Transaction.stock_id == Stock.id, Transaction.user_id == session["user_id"]) \
        .group_by("stock_id").all()

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # use a validation indicator
        validated = True
        # get the values entered by the user
        stock = request.form.get("symbol")
        quantity = int(request.form.get("quantity"))

        # return the DB row for the selected stock
        stock_db = next((stock_db for stock_db in stocks_db if stock_db.stock == stock), None)
        if stock_db is None:
            validated = False
            # add an explicit message to the page
            flash("stock does not exist")
        else:
            if stock_db.quantity < quantity:
                validated = False
                # add an explicit message to the page
                flash("quantity is too high")

        if validated == True:
            # consume the API to get the latest price
            api_response = lookup(stock)
            price = float(api_response["price"])
            # calculate the corresponding amount
            amount = quantity * price
            # proceed with the transaction
            transaction_db = Transaction(stock_id=stock_db.id, user_id=session["user_id"], \
                quantity=-1*quantity, price=price, amount=-1*amount)
            # post the transaction data
            db.session.add(transaction_db)
            # add the amount of the transaction to the user's cash
            user_db = User.query.get(session["user_id"])
            user_db.cash += amount
            # commit changes to validate the transaction
            db.session.commit()

            # add an explicit message to the page
            flash("Sold!")
            # redirect user to home page
            return redirect("/")
        else:
            return render_template("sell.html")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        # get all the stocks currently available
        stocks_db = db.session.query(Stock.stock, db.func.sum(Transaction.quantity).label("quantity")) \
            .filter(Transaction.stock_id == Stock.id, Transaction.user_id == session["user_id"]) \
            .group_by("stock_id").all()

        return render_template("sell.html", stocks=stocks_db)

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    print("Rendering History View")

    # get all the transactions for the user
    transactions_db = db.session.query(Stock.stock, Stock.name, Transaction.quantity, Transaction.price, Transaction.created_on) \
        .filter(Transaction.stock_id == Stock.id, Transaction.user_id == session["user_id"]) \
        .order_by("created_on").all()

    # format the price
    transaction = {}
    transactions = []

    for transaction_db in transactions_db:
        transaction["stock"] = transaction_db.stock
        transaction["name"] = transaction_db.name
        transaction["quantity"] = transaction_db.quantity
        transaction["price"] = transaction_db.price
        transaction["transacted"] = transaction_db.created_on
        transactions.append(transaction.copy())

    return render_template("history.html", transactions=transactions)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    print("Rendering Login View")

    # forget any user_id
    session.clear()
    # set a form validation indicator
    validated = True
    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # query database for username using SQLAlchemy
        user_db = User.query.filter_by(username=request.form.get("username")).first()
        # ensure username exists and password is correct
        if user_db is None or not check_password_hash(user_db.hash, request.form.get("password")):
            validated = False
            # add an explicit message to the page
            flash("invalid username or password")
            # go back to login page
            return render_template("login.html")

        # remember which user has logged in
        session["user_id"] = user_db.id
        # add an explicit message to the page
        flash("Logged in!")
        # redirect user to home page
        return redirect("/")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    print("Rendering Logout View")

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    print("Rendering Register View")

    # forget any user_id
    session.clear()

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # set a form validation indicator
        validated = True
        # query database for username using SQLAlchemy
        user_db_exists = User.query.filter_by(username=request.form.get("username")).count()
        # ensure username does not exist
        if user_db_exists == 1:
            validated = False
            # add an explicit message to the page
            flash("username already exists")
        # ensure password is correct
        if request.form.get("password") != request.form.get("password-confirm") :
            validated = False
            # add an explicit message to the page
            flash("passwords must be identical")

        if validated == False:
            # go back to register page
            return render_template("register.html")

        # create the user based on the model provided
        user_db = User(username=request.form.get("username"),hash=generate_password_hash(request.form.get("password")))
        # add the user to generate an Id
        db.session.add(user_db)
        # commit changes
        db.session.commit()
        # retrieve the Id by querying the DB once again
        user_db = User.query.filter_by(username=request.form.get("username")).first()

        # remember which user has logged in
        if user_db is not None:
            session["user_id"] = user_db.id
            # add an explicit message to the page
            flash("Registered!")
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
