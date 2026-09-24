import os
import uuid

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file
)

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from flask_bcrypt import Bcrypt

from config import Config

from database.database import (
    db,
    User,
    Invoice,
    Expense
)

from preprocessing.image_processing import (
    preprocess_image
)

from ocr.ocr import extract_text

from parser.parser import parse_invoice

from validation.validator import (
    validate_invoice
)

from ml.predictor import (
    predict_category
)

from chatbot.chatbot import (
    answer_question
)

from reports.report import (
    get_weekly_expenses
)


# ---------------------------------
# APP
# ---------------------------------

app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)

bcrypt = Bcrypt(app)


# ---------------------------------
# LOGIN
# ---------------------------------

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )


# ---------------------------------
# FOLDERS
# ---------------------------------

UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "uploads",
    "invoices"
)

PROCESSED_FOLDER = os.path.join(
    app.root_path,
    "uploads",
    "processed"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    PROCESSED_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------------------------------
# HOME
# ---------------------------------

@app.route("/")
def home():

    if current_user.is_authenticated:
        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "index.html"
    )


# ---------------------------------
# LOGIN
# ---------------------------------

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if current_user.is_authenticated:
        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        email = request.form[
            "email"
        ].strip().lower()

        password = request.form[
            "password"
        ]

        user = User.query.filter_by(
            email=email
        ).first()

        if (
            user
            and bcrypt.check_password_hash(
                user.password,
                password
            )
        ):

            login_user(user)

            return redirect(
                url_for("dashboard")
            )

        return render_template(
            "login.html",
            error="Invalid Email or Password",
            email=email
        )

    return render_template(
        "login.html"
    )


# ---------------------------------
# REGISTER
# ---------------------------------

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if current_user.is_authenticated:
        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        name = request.form[
            "name"
        ].strip()

        email = request.form[
            "email"
        ].strip().lower()

        phone = request.form[
            "phone"
        ].strip()

        password = request.form[
            "password"
        ]

        confirm_password = request.form[
            "confirm_password"
        ]

        if password != confirm_password:

            return render_template(
                "register.html",
                error="Passwords do not match.",
                name=name,
                email=email,
                phone=phone
            )

        if User.query.filter_by(
            email=email
        ).first():

            return render_template(
                "register.html",
                error="Email already registered.",
                name=name,
                email=email,
                phone=phone
            )

        if User.query.filter_by(
            phone=phone
        ).first():

            return render_template(
                "register.html",
                error="Phone number already registered.",
                name=name,
                email=email,
                phone=phone
            )

        hashed_password = (
            bcrypt.generate_password_hash(
                password
            ).decode("utf-8")
        )

        user = User(
            name=name,
            email=email,
            phone=phone,
            password=hashed_password
        )

        db.session.add(user)

        db.session.commit()

        flash(
            "Registration Successful! Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ---------------------------------
# DASHBOARD
# ---------------------------------

@app.route("/dashboard")
@login_required
def dashboard():

    invoices = Invoice.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Invoice.uploaded_at.desc()
    ).all()

    expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).all()

    total_spending = sum(
        expense.amount or 0
        for expense in expenses
    )

    categories = set(
        expense.category
        for expense in expenses
        if expense.category
    )

    return render_template(
        "dashboard.html",
        invoices=invoices[:5],
        total_spending=total_spending,
        invoice_count=len(invoices),
        expense_count=len(expenses),
        category_count=len(categories)
    )


# ---------------------------------
# UPLOAD INVOICE
# ---------------------------------

@app.route(
    "/upload",
    methods=["GET", "POST"]
)
@login_required
def upload():

    if request.method == "GET":

        return render_template(
            "upload.html"
        )

    file = request.files.get(
        "invoice"
    )

    if not file or not file.filename:

        flash(
            "Please select an invoice image.",
            "error"
        )

        return redirect(
            url_for("upload")
        )

    allowed = {
        ".jpg",
        ".jpeg",
        ".png"
    }

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    if extension not in allowed:

        flash(
            "Please upload JPG, JPEG or PNG.",
            "error"
        )

        return redirect(
            url_for("upload")
        )

    unique_name = (
        uuid.uuid4().hex
        + extension
    )

    original_path = os.path.join(
        UPLOAD_FOLDER,
        unique_name
    )

    file.save(original_path)

    # -----------------------------
    # OpenCV
    # -----------------------------

    processed_name = (
        "processed_"
        + unique_name
    )

    processed_path = os.path.join(
        PROCESSED_FOLDER,
        processed_name
    )

    try:

        preprocess_image(
            original_path,
            processed_path
        )

        # -------------------------
        # PaddleOCR
        # -------------------------

        raw_text = extract_text(
            processed_path
        )

        # -------------------------
        # Parser
        # -------------------------

        data = parse_invoice(
            raw_text
        )

        # -------------------------
        # Validation
        # -------------------------

        validation = validate_invoice(
            data
        )

        # -------------------------
        # Category
        # -------------------------

        category = predict_category(
            raw_text
        )

        status = (
            "Processed"
            if validation["valid"]
            else "Invalid"
        )

        # -------------------------
        # Invoice
        # -------------------------

        invoice = Invoice(

            user_id=current_user.id,

            original_filename=file.filename,

            stored_filename=unique_name,

            invoice_number=data[
                "invoice_number"
            ],

            vendor=data[
                "vendor"
            ],

            invoice_date=data[
                "invoice_date"
            ],

            subtotal=data[
                "subtotal"
            ] or 0,

            tax=data[
                "tax"
            ] or 0,

            total=data[
                "total"
            ] or 0,

            category=category,

            status=status,

            validation_result=validation[
                "message"
            ],

            raw_ocr_text=raw_text
        )

        db.session.add(invoice)

        db.session.flush()

        # -------------------------
        # Expense
        # -------------------------

        expense = Expense(

            user_id=current_user.id,

            invoice_id=invoice.id,

            amount=data[
                "total"
            ] or 0,

            category=category,

            description=(
                data["vendor"]
                or "Invoice Expense"
            ),

            expense_date=data[
                "invoice_date"
            ]
        )

        db.session.add(expense)

        db.session.commit()

        flash(
            "Invoice processed successfully!",
            "success"
        )

        return redirect(
            url_for(
                "invoice_details",
                invoice_id=invoice.id
            )
        )

    except Exception as e:

        db.session.rollback()

        print(
            "UPLOAD ERROR:",
            e
        )

        flash(
            "Invoice processing failed. "
            "Please check the terminal for details.",
            "error"
        )

        return redirect(
            url_for("upload")
        )


# ---------------------------------
# INVOICES
# ---------------------------------

@app.route("/invoices")
@login_required
def invoices():

    invoices = Invoice.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Invoice.uploaded_at.desc()
    ).all()

    return render_template(
        "invoices.html",
        invoices=invoices
    )


# ---------------------------------
# INVOICE DETAILS
# ---------------------------------

@app.route(
    "/invoice/<int:invoice_id>"
)
@login_required
def invoice_details(
    invoice_id
):

    invoice = Invoice.query.filter_by(
        id=invoice_id,
        user_id=current_user.id
    ).first_or_404()

    return render_template(
        "invoice_details.html",
        invoice=invoice
    )


# ---------------------------------
# EXPENSES
# ---------------------------------

@app.route("/expenses")
@login_required
def expenses():

    expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Expense.created_at.desc()
    ).all()

    return render_template(
        "expenses.html",
        expenses=expenses
    )


# ---------------------------------
# REPORTS
# ---------------------------------

@app.route("/reports")
@login_required
def reports():

    expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).all()

    total = sum(
        expense.amount or 0
        for expense in expenses
    )

    category_totals = {}

    for expense in expenses:

        category = (
            expense.category
            or "Other"
        )

        category_totals[category] = (
            category_totals.get(category, 0)
            + (expense.amount or 0)
        )

    weekly = get_weekly_expenses(
        current_user.id
    )

    return render_template(
        "reports.html",
        expenses=expenses,
        total=total,
        category_totals=category_totals,
        weekly=weekly
    )


# ---------------------------------
# AI CHATBOT
# ---------------------------------

@app.route(
    "/chatbot",
    methods=["GET", "POST"]
)
@login_required
def chatbot():

    if request.method == "POST":

        question = request.form.get(
            "question",
            ""
        ).strip()

        answer = answer_question(
            current_user.id,
            question
        )

        return {
            "answer": answer
        }

    return render_template(
        "chatbot.html"
    )


# ---------------------------------
# PROFILE
# ---------------------------------

@app.route("/profile")
@login_required
def profile():

    return render_template(
        "profile.html"
    )


# ---------------------------------
# EDIT PROFILE
# ---------------------------------

@app.route(
    "/profile/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_profile():

    if request.method == "POST":

        name = request.form[
            "name"
        ].strip()

        email = request.form[
            "email"
        ].strip().lower()

        phone = request.form[
            "phone"
        ].strip()

        existing = User.query.filter(
            User.email == email,
            User.id != current_user.id
        ).first()

        if existing:

            return render_template(
                "edit_profile.html",
                error="Email already registered."
            )

        current_user.name = name
        current_user.email = email
        current_user.phone = phone

        db.session.commit()

        flash(
            "Profile updated successfully.",
            "success"
        )

        return redirect(
            url_for("profile")
        )

    return render_template(
        "edit_profile.html"
    )


# ---------------------------------
# EXCEL EXPORT
# ---------------------------------

@app.route("/export/excel")
@login_required
def export_excel():

    import pandas as pd

    expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).all()

    rows = []

    for expense in expenses:

        rows.append({
            "Date": expense.expense_date,
            "Description": expense.description,
            "Category": expense.category,
            "Amount": expense.amount
        })

    df = pd.DataFrame(rows)

    export_dir = os.path.join(
        app.root_path,
        "exports"
    )

    os.makedirs(
        export_dir,
        exist_ok=True
    )

    file_path = os.path.join(
        export_dir,
        f"expenses_{current_user.id}.xlsx"
    )

    df.to_excel(
        file_path,
        index=False
    )

    return send_file(
        file_path,
        as_attachment=True,
        download_name="my_expenses.xlsx"
    )


# ---------------------------------
# LOGOUT
# ---------------------------------

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("login")
    )


# ---------------------------------
# DATABASE
# ---------------------------------

with app.app_context():

    db.create_all()


# ---------------------------------
# RUN
# ---------------------------------

if __name__ == "__main__":

    app.run(
        debug=True
    )