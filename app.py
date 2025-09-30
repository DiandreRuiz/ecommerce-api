from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Table, Column, ForeignKey, String, DateTime, Float, select
from typing import List
from dotenv import load_dotenv
from datetime import datetime
import os

# DB Connection string
load_dotenv()
DB_CONN_STR = os.getenv("DB_CONN_STR")

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

# --- Models & Junction Tables ---#
order_product = Table(
    "order_product",
    Base.metadata,
    Column("order_id", ForeignKey("orders.id"), primary_key=True),
    Column("product_id", ForeignKey("products.id"), primary_key=True),
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


# --- Schemas ---#
# These schemas define how de-serialization and serialization will
# take place on requests and responses


class UserSchema(marsh.SQLAlchemyAutoSchema):
    class Meta:
        model = User


class OrderSchema(marsh.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
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
users_schema_many = UserSchema(many=True)
orders_schema_many = OrderSchema(many=True)
products_schema_many = ProductSchema(many=True)


# --- API Routes ---#

# /users


@app.route("/users", methods=["GET"])
def get_users():
    query = select(User)
    users = db.session.execute(query).scalars().all()

    return users_schema_many.jsonify(users)


@app.route("/users/<int:id>", methods=["GET"])
def get_user_by_id(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({"message": "Invalid user ID"}), 404
    return users_schema.jsonify(user), 200


@app.route("/users", methods=["POST"])
def create_user():
    # Try to de-serialize request data from request JSON
    try:
        user_data = users_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    # Create new user with validated data
    new_user = User(
        name=user_data["name"], email=user_data["email"], address=user_data["address"]
    )
    db.session.add(new_user)
    db.session.commit()

    return users_schema.jsonify(new_user), 201


@app.route("/users/<int:id>", methods=["PUT"])
def update_user(id):
    # Try to locate the requested user
    user = db.session.get(User, id)
    if not user:
        return jsonify({"message": "Invalid user ID"}), 404

    # Try to deserialize request data into user object
    # NOTE: Because this is a PUT not PATCH operation, we expect
    # a full, valid user object in JSON format
    try:
        user_data = users_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    # If validated request, update user information
    user.name = user_data["name"]
    user.email = user_data["email"]
    user.address = user_data["address"]

    db.session.commit()
    return users_schema.jsonify(user_data), 200


@app.route("/users/<int:id>", methods=["DELETE"])
def delete_user(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({"message": "Invalid user ID"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"succesfully deleted user ID: {id}"}), 200


# /products
@app.route("/products", methods=["GET"])
def get_products():
    query = select(Product)
    products = db.session.execute(query).scalars().all()

    return products_schema_many.jsonify(products), 200


@app.route("/products/<int:id>", methods=["GET"])
def get_product_by_id(id):
    product = db.session.get(Product, id)
    if not product:
        return jsonify({"message": f"Invalid product ID: {id}"}), 404

    return products_schema.jsonify(product), 200


@app.route("/products", methods=["POST"])
def create_product():
    # Try to de-serialize request data into valid product ORM object
    try:
        product_data = products_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    # Product is 'product-schema' python dict that needs to be
    # converted into an ORM Product instantiation
    new_product = Product(
        product_name=product_data["product_name"], price=product_data["price"]
    )
    db.session.add(new_product)
    db.session.commit()

    return products_schema.jsonify(product_data), 201


@app.route("/products/<int:id>", methods=["PUT"])
def update_product(id):
    product = db.session.get(Product, id)
    if not product:
        return jsonify({"message": f"Invalid product id: {id}"}), 404
    # Try to validate contents of PUT request json
    try:
        product_data = products_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    # Update the ORM with requested data
    product.product_name = product_data["product_name"]
    product.price = product_data["price"]
    db.session.commit()

    return products_schema.jsonify(product), 200


@app.route("/products/<int:id>", methods=["DELETE"])
def delete_product(id):
    product = db.session.get(Product, id)
    if not product:
        return jsonify({"message": f"Invalid product ID: {id}"}), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({"message": f"Succesfully deleted Product ID: {id}"}), 200


# Orders


@app.route("/orders", methods=["GET"])
def get_orders():
    query = select(Order)
    orders = db.session.execute(query).scalars().all()

    return orders_schema_many.jsonify(orders), 200


@app.route("/orders/<int:id>", methods=["GET"])
def get_order_by_id(id):
    order = db.session.get(Order, id)
    if not order:
        return jsonify({"message": f"Invalid order ID: {id}"}), 404

    return orders_schema.jsonify(order), 200


@app.route("/orders", methods=["POST"])
def create_order():
    # Validate request.json info for this Order row
    try:
        order_data = orders_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    # Validate that the user_id given in order_data exists
    user = db.session.get(User, order_data["user_id"])
    if not user:
        return jsonify({"message": f"Invalid user ID: {order_data["user_id"]}"}), 404

    # Create entry in database and commit
    new_order = Order(
        order_date_time=order_data["order_date_time"],
        user_id=order_data["user_id"],
    )
    db.session.add(new_order)
    db.session.commit()

    return orders_schema.jsonify(new_order), 201


@app.route("/orders/<int:order_id>/add_product/<int:product_id>", methods=["PUT"])
def add_product_to_order(order_id, product_id):
    # Validate both IDs given
    order = db.session.get(Order, order_id)
    product = db.session.get(Product, product_id)
    if not order:
        return jsonify({"message": f"Invalid order ID: {order_id}"}), 404
    if not product:
        return jsonify({"message": f"Invalid product ID: {product_id}"}), 404

    # Check for uniqueness to prevent duplicates and avoid IntegrityError from SQLAlchemy
    if product in order.products:
        return jsonify(
            {"message": f"product id: {product_id} already in order ID: {order_id}"}
        )

    order.products.append(product)
    db.session.commit()

    return orders_schema.jsonify(order), 200


@app.route("/orders/<int:order_id>/remove_product/<int:product_id>", methods=["DELETE"])
def delete_product_from_order(order_id, product_id):
    # Validate existence of order
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"message": f"Invalid order ID: {order_id}"}), 404
    # Validate existence of product
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"message": f"Invalid product ID: {product_id}"}), 404
    # Validate relationship between order and product
    if product not in order.products:
        return jsonify({"message": f"Product {product_id} not in {order_id}"}), 400

    # Remove product from this order
    order.products.remove(product)
    db.session.commit()

    return (
        jsonify({"message": f"Removed product {product_id} from order {order_id}"}),
        200,
    )


@app.route("/orders/user/<int:user_id>", methods=["GET"])
def get_all_orders_for_userid(user_id):
    # Validate user_id
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": f"Invalid user_id: {user_id}"}), 404

    # Get all orders for this user_id
    orders = user.orders
    return orders_schema_many.jsonify(orders), 200


@app.route("/orders/<int:order_id>/products", methods=["GET"])
def get_order_products_for_orderid(order_id):
    # Validate order_id exists
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"message": f"Invalid order_id: {order_id}"}), 404

    products = order.products
    return products_schema_many.jsonify(products), 200


# Check dunder so if called directly, this
# modules creates all the tables from scratch
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

app.run(debug=True)
