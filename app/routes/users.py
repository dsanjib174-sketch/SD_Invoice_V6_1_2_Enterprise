from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from .auth import login_required
import os, json, uuid
from datetime import datetime
from werkzeug.security import generate_password_hash

users_bp = Blueprint("users", __name__)

USERS_FILE = "users.json"
CLIENTS_FILE = "clients.json"


def _json_path(filename):
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        upload_folder = os.path.join(current_app.root_path, "data")
    os.makedirs(upload_folder, exist_ok=True)
    return os.path.join(upload_folder, filename)


def load_json(filename):
    path = _json_path(filename)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_json(filename, data):
    path = _json_path(filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def current_user_email():
    return session.get("user") or session.get("email") or ""


def is_superadmin():
    return session.get("login_type") == "superadmin" or session.get("role") == "superadmin"


def visible_users(users):
    if is_superadmin():
        return users
    return [u for u in users if u.get("client_email") == current_user_email()]


@users_bp.route("/users", methods=["GET", "POST"])
@login_required
def users():
    users_data = load_json(USERS_FILE)
    clients = load_json(CLIENTS_FILE)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "user").strip()
        branch = request.form.get("branch", "").strip()
        status = request.form.get("status", "Active").strip()

        if is_superadmin():
            client_email = request.form.get("client_email", "").strip().lower()
        else:
            client_email = current_user_email()

        if not name or not email or not password:
            flash("Name, email and password are required.", "error")
            return redirect(url_for("users.users"))

        existing = next((u for u in users_data if u.get("email") == email), None)
        if existing:
            flash("User already exists with this email.", "error")
            return redirect(url_for("users.users"))

        users_data.insert(0, {
            "id": uuid.uuid4().hex,
            "name": name,
            "email": email,
            "password": generate_password_hash(password),
            "plain_password": password,
            "role": role,
            "branch": branch,
            "status": status,
            "client_email": client_email,
            "created_by": current_user_email(),
            "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        })

        save_json(USERS_FILE, users_data)
        flash("User created successfully.", "success")
        return redirect(url_for("users.users"))

    return render_template(
        "users/index.html",
        users=visible_users(users_data),
        clients=clients,
        is_superadmin=is_superadmin()
    )
