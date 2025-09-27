from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Table, Column, ForeignKey, String, DateTime, Float, select
from typing import List
from dotenv import load_dotenv
from datetime import datetime

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

#--- Models & Junction Tables ---#
order_product = Table(
    "order_product",
    Base.metadata,
    Column("order_id", ForeignKey("order.id"), primary_key=True),
    Column("product_id", ForeignKey("product.id"), primary_key=True),
)


# This creates the table and defines the attributes that every instance of User should have (row in users table)
# These models automatically get added to the Base.metadata due to their inheritence from Base
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    address: Mapped[str] = mapped_column(String(100), nullable=True)
    # We don't need an orders column, just being able to access via ORM convenience
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_date_time: Mapped[datetime] = mapped_column(DateTime(False), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # ORM dot-notation convenience feature
    user: Mapped["User"] = relationship("User", back_populates="orders")
    products: Mapped[List["Product"]] = relationship(
        "Product", secondary="order_product", back_populates="orders"
    )


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    price: Mapped[float] = mapped_column(Float(2), nullable=False)
    orders: Mapped[List["Order"]] = relationship(
        "Order", secondary="order_product", back_populates="products"
    )

#--- Schemas ---#
# These schemas define how de-serialization and serialization will
# take place on requests and responses

class UserSchema(marsh.SQLAlchemyAutoSchema):
    class Meta:
        model = User

class OrderSchema(marsh.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_fk = True

class ProductSchema(marsh.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        include_fk = True
 
# schema object instantiation which has 
# (de)serialization methods from their parent classes       
users_schema = UserSchema()
orders_schema = OrderSchema()
products_schema = ProductSchema()

#--- API Routes ---#
@app.route("/users", methods=["GET"])
def get_users():
    query = select(User)
    users = db.session.execute(query).scalars().all()
    
    return users_schema.jsonify(users)

