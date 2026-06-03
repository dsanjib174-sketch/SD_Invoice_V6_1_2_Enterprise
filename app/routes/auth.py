from flask import Blueprint, render_template, request, redirect, session, Response, url_for, flash, current_app
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os, json, uuid
from datetime import datetime

auth_bp = Blueprint("auth", __name__)
USERS_FILE = "users.json"


def _json_path(filename):
    return os.path.join(current_app.config["UPLOAD_FOLDER"], filename)


def save_users(items):
    os.makedirs(os.path.dirname(_json_path(USERS_FILE)), exist_ok=True)
    with open(_json_path(USERS_FILE), "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def default_users():
    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    return [
        {
            "id": uuid.uuid4().hex,
            "name": "Super Admin",
            "email": "superadmin@sdinvoice.com",
            "user_id": "superadmin@sdinvoice.com",
            "password": generate_password_hash("Admin@123"),
            "role": "superadmin",
            "branch": "All Branches",
            "company": "SMART DADA SOLUTION",
            "status": "Active",
            "client_email": "superadmin@sdinvoice.com",
            "created_at": now
        },
        {
            "id": uuid.uuid4().hex,
            "name": "Demo Client",
            "email": "demo@sdinvoice.com",
            "user_id": "demo@sdinvoice.com",
            "password": generate_password_hash("Demo@123"),
            "role": "client",
            "branch": "Main Branch",
            "company": "Demo Company",
            "status": "Active",
            "client_email": "demo@sdinvoice.com",
            "created_by": "demo@sdinvoice.com",
            "created_at": now
        }
    ]


def load_users():
    path = _json_path(USERS_FILE)
    if not os.path.exists(path):
        users = default_users()
        save_users(users)
        return users
    with open(path, "r", encoding="utf-8") as f:
        users = json.load(f)
    existing = {u.get("email") for u in users}
    changed = False
    for u in default_users():
        if u.get("email") not in existing:
            users.append(u)
            changed = True
    if changed:
        save_users(users)
    return users


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("login_type"):
            return redirect(url_for("auth.client_login"))
        return view(*args, **kwargs)
    return wrapped


def superadmin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("login_type") != "superadmin":
            flash("Super Admin access required.", "error")
            return redirect(url_for("dashboard.dashboard"))
        return view(*args, **kwargs)
    return wrapped


def authenticate_user(user_id, password, required_role=None):
    for u in load_users():
        if u.get("status") != "Active":
            continue
        if u.get("user_id") == user_id or u.get("email") == user_id:
            if required_role and u.get("role") != required_role:
                return None
            stored = u.get("password", "")
            if stored.startswith("pbkdf2:") or stored.startswith("scrypt:"):
                if check_password_hash(stored, password):
                    return u
            elif stored == password:
                return u
    return None


def set_login_session(user, login_type):
    session["login_type"] = login_type
    session["user"] = user.get("email")
    session["email"] = user.get("email")
    session["user_id"] = user.get("user_id")
    session["user_name"] = user.get("name")
    session["role"] = user.get("role")
    session["branch"] = user.get("branch")
    session["client_name"] = "All Clients" if login_type == "superadmin" else user.get("company", "Client")


@auth_bp.route("/", methods=["GET", "POST", "HEAD"])
def client_login():
    if request.method == "HEAD":
        return Response(status=200)
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "").strip()
        user = authenticate_user(user_id, password)
        if user and user.get("role") != "superadmin":
            set_login_session(user, "client")
            return redirect("/dashboard")
        flash("Invalid client login ID or password.", "error")
    return render_template("auth/client_login.html", login_mode="Client Login")


@auth_bp.route("/admin", methods=["GET", "POST", "HEAD"])
def admin_login():
    if request.method == "HEAD":
        return Response(status=200)
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "").strip()
        user = authenticate_user(user_id, password, required_role="superadmin")
        if user:
            set_login_session(user, "superadmin")
            return redirect("/dashboard")
        flash("Invalid Super Admin login ID or password.", "error")
    return render_template("auth/client_login.html", login_mode="Super Admin Login", admin=True)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@auth_bp.route("/forgot-password")
def forgot_password():
    return render_template("auth/forgot_password.html")
