from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Table, Column, ForeignKey, String, select
from dotenv import load_dotenv

# DB Connection string
DB_CONN_STR = load_dotenv("DB_CONN_STR")

# Create flask app client w/ name of __main__ or app.py
app = Flask(__name__)

# Configure MySQL data in app w/ db connection URI
app.config["SQLALCHEMY_DATABASE_URI"] = DB_CONN_STR


# Creation of Base Model we will use to store to metadata
class Base(DeclarativeBase):
    pass


# Initialize SQLAlchemy and marshmallow
db = SQLAlchemy(model_class=Base)
db.init_app(app)
marsh = Marshmallow(app)

# Models & Junction Tables
# order_product =
