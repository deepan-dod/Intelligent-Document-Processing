from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    phone = db.Column(
        db.String(20),
        unique=True
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    invoices = db.relationship(
        "Invoice",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    original_filename = db.Column(
        db.String(255)
    )

    stored_filename = db.Column(
        db.String(255)
    )

    invoice_number = db.Column(
        db.String(100)
    )

    vendor = db.Column(
        db.String(200)
    )

    invoice_date = db.Column(
        db.String(50)
    )

    subtotal = db.Column(
        db.Float,
        default=0
    )

    tax = db.Column(
        db.Float,
        default=0
    )

    total = db.Column(
        db.Float,
        default=0
    )

    category = db.Column(
        db.String(100),
        default="Uncategorized"
    )

    status = db.Column(
        db.String(50),
        default="Processed"
    )

    validation_result = db.Column(
        db.String(255)
    )

    raw_ocr_text = db.Column(
        db.Text
    )

    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    expense = db.relationship(
        "Expense",
        backref="invoice",
        uselist=False,
        cascade="all, delete-orphan"
    )


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("invoices.id"),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    category = db.Column(
        db.String(100),
        nullable=False,
        default="Uncategorized"
    )

    description = db.Column(
        db.String(255)
    )

    expense_date = db.Column(
        db.String(50)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
