import os
import sys
import logging
import requests

# from cs50 import SQL
from flask import Flask, flash, json, jsonify, redirect, render_template, request, session
from flask.logging import default_handler
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import select
from sqlalchemy.sql import func
from logging import Formatter
# local packages
from models import *
from helpers import apology, login_required, lookup, usd, percentage

# configure application
app = Flask(__name__)

# create log formatter
formatter = Formatter("%(message)s")
default_handler.setFormatter(formatter)
# configure Flask logger
app.logger.addHandler(default_handler)

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

# configure CS50 library to use SQLite database
# db = SQL("sqlite:///finance.db")

# get DB host if exists
if os.environ.get("DATABASE_HOST"):
    dbhost = os.environ.get("DATABASE_HOST")
else:
    dbhost = ""

# configure DB to interact with Flask
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite://{dbhost}/finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# initialize app
app.logger.debug("Initializing the Flask application...")
# https://stackoverflow.com/questions/9692962/flask-sqlalchemy-import-context-issue/9695045#9695045
app.logger.debug("Initializing the application DB...")
db.init_app(app)
# push the context so that DB operations are performed inside an application context
app.logger.debug("Initializing the application context...")
app.app_context().push()
# get models & create corresponding DB tables if necessary
app.logger.debug("Creating/Updating the application model...")
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
    app.logger.debug("Index")

    # get current user's balance
    user_db = User.get_by_id(session["user_id"])
    # get all the stocks currently available
    stocks_db = Stock.get_all(user_id=user_db.id)
    # lookup for current price/calculate the grand total
    grand_total = user_db.cash
    # convert object to array for template proccessing
    transaction = {}
    transactions = []

    # https://stackoverflow.com/questions/16279212/how-to-use-dot-notation-for-dict-in-python
    valid_stocks_db = (stock_db for stock_db in stocks_db if stock_db.quantity > 0)

    for transaction_db in valid_stocks_db:
        transaction["stock"] = transaction_db.stock
        transaction["name"] = transaction_db.name
        transaction["quantity"] = transaction_db.quantity
        # lookup for current price
        api_response = lookup(transaction_db.stock)
        price = float(api_response["price"])
        transaction["price"] = price
        # define a comparison indicator on the price (latest) vs average price (DB)
        avg_price = float(transaction_db.amount / transaction_db.quantity)

        avg_price_5 = round(avg_price, 5)
        price_5 = round(price, 5)

        if price_5 > avg_price_5:
            transaction["price_indicator"] = "table-success"
        elif price_5 < avg_price_5:
            transaction["price_indicator"] = "table-danger"
        else:
            transaction["price_indicator"] = "table-secondary"

        # the price variation is calculated based on historical average vs latest price
        transaction["variation"] = ((price - avg_price) / avg_price)
        # the amount is valuated based on the latest price
        amount = float(transaction_db.quantity * price)
        transaction["amount"] = amount
        transactions.append(transaction.copy())

        grand_total += amount

    app.logger.debug("Render Index view")
    return render_template("index.html", transactions=transactions, cash=user_db.cash, grand_total=grand_total)

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """
    Get stock quote.

    example of API call:
    https://cloud.iexapis.com/stable/stock/aapl/quote?token=API_TOKEN
    """
    app.logger.debug("Quote")

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # consume the API to get the latest price
        api_response = lookup(request.form.get("stock"))
        # check for potential errors
        if api_response is None:
            # add an explicit message to the page
            flash("Stock does not exist")
            # go back to quote page
            app.logger.debug("Render Quote view from POST")
            return render_template("quote_request.html")
        else:
            # format the amount in USD
            amount = api_response["price"]

            app.logger.debug("Render Quote view from POST")
            return render_template("quote_response.html", stock=api_response["symbol"], name=api_response["name"], amount=amount)
    # user reached route via GET (as by clicking a link or via redirect)
    else:
        app.logger.debug("Render Quote view from GET")
        return render_template("quote_request.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    app.logger.debug("Buy")

    # user reached route via POST
    if request.method == "POST":
        validated = True
        # consume the API to get the latest price
        api_response = lookup(request.form.get("symbol"))
        # check for potential errors
        if api_response is None:
            validated = False
            # add an explicit message to the page
            flash("stock does not exist")
        else:
            # calculate the transaction amount to check whether the user can afford to purchase these stocks
            amount = float(request.form.get("shares")) * float(api_response["price"])
            # query the DB to get the cash available for the user
            user_db = User.get_by_id(session["user_id"])
            if user_db.cash < amount:
                validated = False
                # add an explicit message to the page
                flash("balance too low")
            else:
                # update the transaction & the stock tables
                stock_db_exists = Stock.exist_by_name(name=api_response["name"])

                if stock_db_exists is False:
                    # add the stock to the master data
                    stock_db = Stock(stock=api_response["symbol"], name=api_response["name"])
                    # post the master data
                    db.session.add(stock_db)
                    # commit changes to get an Id for the stock
                    db.session.commit()

                stock_db = Stock.get_by_name(name=api_response["name"])
                # add the transaction to the transaction data
                transaction_db = Transaction(stock_id=stock_db.id, user_id=session["user_id"], \
                    quantity=int(request.form.get("shares")), price=float(api_response["price"]), amount=amount)
                # post the transaction data
                db.session.add(transaction_db)
                # subtract the amount of the transaction to the user's cash
                user_db.cash -= amount
                # commit changes to validate the transaction
                db.session.commit()

                # add an explicit message to the page
                flash("Bought!")
                # redirect user to home page
                app.logger.debug("Redirect to Index view from POST")
                return redirect("/")

        if validated == False:
            # go back to buy page
            app.logger.debug("Render Buy view from POST")
            return render_template("buy.html")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        app.logger.debug("Render Buy view from GET")
        return render_template("buy.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    app.logger.debug("Sell")

    # get current user
    user_db = User.get_by_id(session["user_id"])
    # get all the stocks currently available
    stocks_db = Stock.get_all(user_id=user_db.id)

    # https://stackoverflow.com/questions/16279212/how-to-use-dot-notation-for-dict-in-python
    valid_stocks_db = (stock_db for stock_db in stocks_db if stock_db.quantity > 0)

    # user reached route via POST
    if request.method == "POST":
        validated = True
        # get the values entered by the user
        stock = request.form.get("symbol")
        quantity = int(request.form.get("shares"))

        # return the DB row for the selected stock
        stock_db = next((stock_db for stock_db in valid_stocks_db if stock_db.stock == stock), None)
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
            # add the transaction to the transaction data
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
            app.logger.debug("Redirect to Index view from POST")
            return redirect("/")
        else:
            app.logger.debug("Render Sell view from POST")
            return render_template("sell.html", stocks=valid_stocks_db)

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        app.logger.debug("Render Sell view from GET")
        return render_template("sell.html", stocks=valid_stocks_db)

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    app.logger.debug("History")

    # get current user
    user_db = User.get_by_id(session["user_id"])
    # get all the transactions for the user
    transactions_db = Transaction.get_all(user_id=user_db.id)
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

    app.logger.debug("Render History view")
    return render_template("history.html", transactions=transactions)

# routes for Ajax requests
@app.route("/buy_1", methods=["POST"])
@login_required
def buy_1():
    """Buy 1 share of stock"""
    app.logger.debug("Buy 1 share from Button")

    # user reached route via form POST
    validated = True
    message = None
    # replace single quotes with double quotes if necessary to get valid JSON
    transaction = json.loads(request.form.get("transaction").replace("\'", "\""))
    dis_total = float(json.loads(request.form.get("grand_total").replace("\'", "\"")))
    # consume the API to get the latest price
    api_response = lookup(transaction["stock"])
    # check for potential errors
    if api_response is None:
        validated = False
        message = "stock does not exist"
    else:
        # check whether the user can afford to purchase an additional stock
        cur_price = float(api_response["price"])
        # query the DB to get the cash available for the user
        user_db = User.get_by_id(session["user_id"])
        if user_db.cash < cur_price:
            validated = False
            message = "balance too low"
        else:
            stock_db = Stock.get_by_name(name=api_response["name"])
            # add the transaction to the transaction data
            transaction_db = Transaction(stock_id=stock_db.id, user_id=session["user_id"], \
                quantity=1, price=cur_price, amount=cur_price)
            # post the transaction data
            db.session.add(transaction_db)
            # subtract the amount of the transaction to the user's cash
            user_db.cash -= cur_price
            # commit changes to validate the transaction
            db.session.commit()

        if validated == True:
            # recalculate the figures for the selected stock
            transaction_db = Transaction.get_by_symbol(user_id=user_db.id, symbol=api_response["symbol"])
            # define a comparison indicator on the price (latest) vs average price (DB)
            avg_price = float(transaction_db.amount / transaction_db.quantity)
            dis_price = float(transaction["price"])
            amount = float(transaction_db.quantity * cur_price)
            variation = (cur_price - avg_price) / avg_price

            # update the figures from the existing one (raw data not converted)
            transaction["quantity"] = transaction_db.quantity
            transaction["price"] = cur_price
            transaction["amount"] = amount
            transaction["variation"] = variation
            if (variation < 0):
                transaction["price_indicator"] = "table-danger"
            elif (variation == 0):
                transaction["price_indicator"] = "table-secondary"
            else:
                transaction["price_indicator"] = "table-success"

            grand_total = dis_total - dis_price + cur_price
            # server-side rendering for filtered values
            return jsonify({"success": True, "transaction": transaction, "cash": usd(user_db.cash), "price": usd(cur_price), \
                "amount": usd(amount), "variation": percentage(variation), "grand_total": usd(grand_total)})
        else:
            return jsonify({"success": False, "message": message})

@app.route("/sell_1", methods=["POST"])
@login_required
def sell_1():
    """Sell 1 share of stock"""
    app.logger.debug("Sell 1 share from Button")

    # user reached route via form POST
    validated = True
    message = None
    # replace single quotes with double quotes if necessary to get valid JSON
    transaction = json.loads(request.form.get("transaction").replace("\'", "\""))
    dis_total = float(json.loads(request.form.get("grand_total").replace("\'", "\"")))
    # consume the API to get the latest price
    api_response = lookup(transaction["stock"])
    # check for potential errors
    if api_response is None:
        validated = False
        message = "stock does not exist"
    else:
        cur_price = float(api_response["price"])
        # query the DB to get the cash available for the user
        user_db = User.get_by_id(session["user_id"])
        # check whether the quantity for this stock is enough
        stock_db = Transaction.get_by_symbol(user_id=user_db.id, symbol=api_response["symbol"])

        if stock_db.quantity < 1:
            validated = False
            message = "no more stock to sell"
        else:
            # add the transaction to the transaction data
            transaction_db = Transaction(stock_id=stock_db.id, user_id=session["user_id"], \
                quantity=-1, price=cur_price, amount=-cur_price)
            # post the transaction data
            db.session.add(transaction_db)
            # add the amount of the transaction to the user's cash
            user_db.cash += cur_price
            # commit changes to validate the transaction
            db.session.commit()

        if validated == True:
            # recalculate the figures for the selected stock
            transaction_db = Transaction.get_by_symbol(user_id=user_db.id, symbol=api_response["symbol"])
            # define a comparison indicator on the price (latest) vs average price (DB)
            avg_price = float(transaction_db.amount / transaction_db.quantity) if transaction_db.quantity > 0 else 0
            dis_price = float(transaction["price"])
            amount = float(transaction_db.quantity * cur_price)
            variation = (cur_price - avg_price) / avg_price if avg_price > 0 else 0

            # update the figures from the existing one (raw data not converted)
            transaction["quantity"] = transaction_db.quantity
            transaction["price"] = cur_price
            transaction["amount"] = amount
            transaction["variation"] = variation
            if (variation < 0):
                transaction["price_indicator"] = "table-danger"
            elif (variation == 0):
                transaction["price_indicator"] = "table-secondary"
            else:
                transaction["price_indicator"] = "table-success"

            grand_total = dis_total + dis_price - cur_price
            # server-side rendering for filtered values
            return jsonify({"success": True, "transaction": transaction, "cash": usd(user_db.cash), "price": usd(cur_price), \
                "amount": usd(amount), "variation": percentage(variation), "grand_total": usd(grand_total)})
        else:
            return jsonify({"success": False, "message": message})

# routes for user management
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    app.logger.debug("Login")

    # forget any user_id
    session.clear()

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username").lower()
        # query database for username using SQLAlchemy
        user_db = User.get_by_username(username=username)
        # ensure username exists and password is correct
        if user_db is None or not check_password_hash(user_db.hash, request.form.get("password")):
            # add an explicit message to the page
            flash("invalid username or password")
            # go back to login page
            app.logger.debug("Render Login view from Login POST")
            return render_template("login.html")

        # remember which user has logged in
        session["user_id"] = user_db.id
        # add an explicit message to the page
        flash("Logged in!")
        # redirect user to home page
        app.logger.debug("Redirect to Index view from Login POST")
        return redirect("/")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        app.logger.debug("Render Login view from Login GET")
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    app.logger.debug("Logout")

    # forget any user_id
    session.clear()

    # redirect user to login form
    app.logger.debug("Redirect to Login view from GET")
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    app.logger.debug("Register")

    # forget any user_id
    session.clear()

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        validated = True
        username = request.form.get("username").lower()
        # query database for username using SQLAlchemy
        user_db_exists = User.exist_by_username(username=username)
        # ensure username does not exist
        if user_db_exists is True:
            validated = False
            # add an explicit message to the page
            flash("username already exists")
        # ensure password is correct
        if request.form.get("password") != request.form.get("confirmation") :
            validated = False
            # add an explicit message to the page
            flash("passwords must be identical")

        if validated == False:
            # go back to register page
            app.logger.debug("Render Register view from POST")
            return render_template("register.html")

        # create the user in the DB
        user_db = User.create(username=username,hash=generate_password_hash(request.form.get("password")))

        if user_db is not None:
            # register the first user transaction (cash = 10000)
            Transaction.create(user_id=user_db.id, amount=float(10000), visible=False)
            # remember which user has logged in
            session["user_id"] = user_db.id
            # add an explicit message to the page
            flash("Registered!")
            # redirect user to home page
            app.logger.debug("Redirect to Index view from POST")
            return redirect("/")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        app.logger.debug("Render Register view from GET")
        return render_template("register.html")

def errorhandler(e):
    """Handle error"""
    if isinstance(e, HTTPException):
        app.logger.error("http exception raised: ", e)
    else:
        e = InternalServerError()
        app.logger.error("internal exception raised: ", e)
    return apology(e.name, e.code)

# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
