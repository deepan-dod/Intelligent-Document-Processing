from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from database.models import User
from auth.security import bcrypt
from audit import audit_log as audit

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form.get("username", "")).first()
        if u and u.active and bcrypt.check_password_hash(u.password_hash, request.form.get("password", "")):
            login_user(u); audit.log("login", user=u.username, source="human")
            next_url = request.args.get("next") or request.form.get("next")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("web.dashboard"))
        flash("Login failed: Invalid credentials")
    return render_template("login.html", next=request.args.get("next", ""))

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
