from functools import wraps
from flask import jsonify, request, redirect, url_for, flash
from flask_login import current_user

ROLES = ("admin", "investigator", "reviewer", "auditor")
PERMS = {  # RBAC matrix
    "upload": {"admin", "investigator"},
    "correct": {"admin", "investigator"},
    "decide": {"admin", "investigator", "reviewer"},
    "manage": {"admin"},
    "read": set(ROLES),
}

def can(perm):
    return current_user.is_authenticated and current_user.role in PERMS.get(perm, set())

def require(perm):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **k):
            if not current_user.is_authenticated:
                if request.path.startswith("/api"):
                    return jsonify(error="authentication required"), 401
                return redirect(url_for("auth.login", next=request.full_path if request.query_string else request.path))
            if not can(perm):
                if request.path.startswith("/api"):
                    return jsonify(error="forbidden", required=perm), 403
                flash(f"Access denied: '{perm}' permission required (current role: {current_user.role})")
                return redirect(url_for("web.dashboard"))
            return fn(*a, **k)
        return wrapper
    return deco
