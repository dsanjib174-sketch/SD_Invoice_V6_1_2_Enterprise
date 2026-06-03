from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.security import generate_password_hash
from .auth import login_required
import os, json, uuid
from datetime import datetime

client_bp = Blueprint("client", __name__)
USERS_FILE = "users.json"
BRANCHES_FILE = "branches.json"


def _json_path(filename):
    return os.path.join(current_app.config["UPLOAD_FOLDER"], filename)


def load_json(filename, default_value=None):
    if default_value is None:
        default_value = []
    path = _json_path(filename)
    if not os.path.exists(path):
        return default_value
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, items):
    os.makedirs(os.path.dirname(_json_path(filename)), exist_ok=True)
    with open(_json_path(filename), "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def load_users():
    return load_json(USERS_FILE, [])


def save_users(items):
    save_json(USERS_FILE, items)


def current_client_email():
    return session.get("user") or session.get("email") or ""


def is_superadmin():
    return session.get("login_type") == "superadmin" or session.get("role") == "superadmin"


def load_branches():
    branches = load_json(BRANCHES_FILE, [])
    if not branches:
        branches = [{"id": uuid.uuid4().hex, "branch_name": "Main Branch", "branch_code": "MAIN", "client_email": current_client_email()}]
        save_json(BRANCHES_FILE, branches)
    if is_superadmin():
        return branches
    email = current_client_email()
    return [b for b in branches if b.get("client_email") in ("", email) or b.get("created_by") == email]


def visible_users_for_current_login(users_data):
    if is_superadmin():
        return users_data
    email = current_client_email()
    return [u for u in users_data if u.get("role") != "superadmin" and (u.get("client_email") == email or u.get("created_by") == email or u.get("email") == email)]


@client_bp.route("/company-profile")
@login_required
def company_profile():
    return render_template("client/company_profile.html")


@client_bp.route("/branches")
@login_required
def branches():
    return render_template("client/branches.html")


@client_bp.route("/users", methods=["GET", "POST"])
@login_required
def users():
    users_data = load_users()
    branches_data = load_branches()
    login_email = current_client_email()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            user_id = request.form.get("user_id", "").strip()
            password = request.form.get("password", "").strip()
            branch = request.form.get("branch", "").strip()
            status = request.form.get("status", "Active").strip()
            if not name or not email or not user_id or not password:
                flash("Name, Email, User ID and Password are required.", "error")
                return redirect(url_for("client.users"))
            for u in users_data:
                if u.get("user_id") == user_id or u.get("email") == email:
                    flash("User ID or Email already exists.", "error")
                    return redirect(url_for("client.users"))
            role = request.form.get("role", "client").strip() if is_superadmin() else "client"
            client_email = request.form.get("client_email", "").strip() if is_superadmin() else login_email
            users_data.insert(0, {
                "id": uuid.uuid4().hex,
                "name": name,
                "email": email,
                "user_id": user_id,
                "password": generate_password_hash(password),
                "role": role,
                "branch": branch,
                "status": status,
                "client_email": client_email or email,
                "created_by": login_email,
                "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
            })
            save_users(users_data)
            flash("User added successfully.", "success")
        elif action == "update":
            record_id = request.form.get("user_record_id")
            new_password = request.form.get("password", "").strip()
            for u in users_data:
                if u.get("id") == record_id:
                    if not is_superadmin() and u.get("role") == "superadmin":
                        flash("You cannot update Super Admin user.", "error")
                        return redirect(url_for("client.users"))
                    if not is_superadmin() and u.get("client_email") != login_email and u.get("email") != login_email:
                        flash("You cannot update another client's user.", "error")
                        return redirect(url_for("client.users"))
                    u["name"] = request.form.get("name", "").strip()
                    u["email"] = request.form.get("email", "").strip()
                    u["user_id"] = request.form.get("user_id", "").strip()
                    u["branch"] = request.form.get("branch", "").strip()
                    u["status"] = request.form.get("status", "Active").strip()
                    u["role"] = request.form.get("role", "client").strip() if is_superadmin() else "client"
                    if is_superadmin():
                        u["client_email"] = request.form.get("client_email", u.get("client_email", "")).strip()
                    if new_password:
                        u["password"] = generate_password_hash(new_password)
                    u["updated_at"] = datetime.now().strftime("%d-%m-%Y %I:%M %p")
                    break
            save_users(users_data)
            flash("User updated successfully.", "success")
        return redirect(url_for("client.users"))

    return render_template("client/users.html", users=visible_users_for_current_login(users_data), branches=branches_data)


@client_bp.route("/change-password")
@login_required
def change_password():
    return render_template("client/change_password.html")


@client_bp.route("/communication")
@login_required
def communication():
    return render_template("client/communication.html")
