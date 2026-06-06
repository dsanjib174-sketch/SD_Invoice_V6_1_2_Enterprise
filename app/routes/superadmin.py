from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import os
import json
import uuid

from .auth import login_required, superadmin_required

superadmin_bp = Blueprint("superadmin", __name__)

CLIENTS_FILE = "clients.json"
USERS_FILE = "users.json"
PLANS_FILE = "plans.json"
UPDATES_FILE = "updates.json"
AUDIT_FILE = "audit_logs.json"

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


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


def add_audit(action, document_type, document_no, client_email="", amount="0"):
    logs = load_json(AUDIT_FILE)

    logs.insert(0, {
        "id": uuid.uuid4().hex,
        "action": action,
        "document_type": document_type,
        "document_no": document_no,
        "amount": amount,
        "client_email": client_email,
        "created_by": current_user_email(),
        "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
    })

    save_json(AUDIT_FILE, logs)


def default_plans():
    return [
        {
            "id": uuid.uuid4().hex,
            "plan": "Trial Plan",
            "price": "0",
            "user_limit": "1",
            "branch_limit": "1",
            "invoice_limit": "25",
            "validity_days": "7",
            "status": "Active",
            "updated_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        },
        {
            "id": uuid.uuid4().hex,
            "plan": "Basic Plan",
            "price": "2999",
            "user_limit": "2",
            "branch_limit": "1",
            "invoice_limit": "300",
            "validity_days": "365",
            "status": "Active",
            "updated_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        },
        {
            "id": uuid.uuid4().hex,
            "plan": "Standard Plan",
            "price": "5999",
            "user_limit": "5",
            "branch_limit": "3",
            "invoice_limit": "1000",
            "validity_days": "365",
            "status": "Active",
            "updated_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        },
        {
            "id": uuid.uuid4().hex,
            "plan": "Enterprise Plan",
            "price": "14999",
            "user_limit": "25",
            "branch_limit": "10",
            "invoice_limit": "Unlimited",
            "validity_days": "365",
            "status": "Active",
            "updated_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        }
    ]


def get_plan_by_name(plan_name):
    plans_data = load_json(PLANS_FILE)

    if not plans_data:
        plans_data = default_plans()
        save_json(PLANS_FILE, plans_data)

    return next(
        (p for p in plans_data if p.get("plan") == plan_name),
        {}
    )


@superadmin_bp.route("/superadmin/clients", methods=["GET", "POST"])
@login_required
@superadmin_required
def clients():
    clients_data = load_json(CLIENTS_FILE)
    users_data = load_json(USERS_FILE)
    plans_data = load_json(PLANS_FILE)

    if not plans_data:
        plans_data = default_plans()
        save_json(PLANS_FILE, plans_data)

    if request.method == "POST":
        company = request.form.get("company", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        plan_name = request.form.get("plan_name", "").strip()

        selected_plan = get_plan_by_name(plan_name)

        user_limit = request.form.get("user_limit", "").strip() or selected_plan.get("user_limit", "1")
        branch_limit = request.form.get("branch_limit", "").strip() or selected_plan.get("branch_limit", "1")
        invoice_limit = request.form.get("invoice_limit", "").strip() or selected_plan.get("invoice_limit", "100")
        validity_days = request.form.get("validity_days", "").strip() or selected_plan.get("validity_days", "365")

        active_date = request.form.get("active_date", "").strip()
        expire_date = request.form.get("expire_date", "").strip()
        expire_comment = request.form.get("expire_comment", "").strip()
        status = request.form.get("status", "Active").strip()

        if not company or not email or not password:
            flash("Company, email and password are required.", "error")
            return redirect(url_for("superadmin.clients"))

        existing_client = next(
            (c for c in clients_data if c.get("email") == email),
            None
        )

        if existing_client:
            flash("Client already exists with this email.", "error")
            return redirect(url_for("superadmin.clients"))

        if not active_date:
            active_dt = datetime.now()
            active_date = active_dt.strftime("%Y-%m-%d")
        else:
            active_dt = datetime.strptime(active_date, "%Y-%m-%d")

        if not expire_date:
            try:
                expire_date = (
                    active_dt + timedelta(days=int(validity_days))
                ).strftime("%Y-%m-%d")
            except Exception:
                expire_date = (
                    active_dt + timedelta(days=365)
                ).strftime("%Y-%m-%d")

        client_id = uuid.uuid4().hex

        client_record = {
            "id": client_id,
            "company": company,
            "email": email,
            "plan_name": plan_name,
            "user_limit": user_limit,
            "branch_limit": branch_limit,
            "invoice_limit": invoice_limit,
            "validity_days": validity_days,
            "active_date": active_date,
            "expire_date": expire_date,
            "expire_comment": expire_comment,
            "status": status,
            "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p"),
            "created_by": current_user_email()
        }

        clients_data.insert(0, client_record)
        save_json(CLIENTS_FILE, clients_data)

        users_data.insert(0, {
            "id": uuid.uuid4().hex,
            "name": company,
            "email": email,
            "password": generate_password_hash(password),
            "plain_password": password,
            "role": "client_admin",
            "branch": "Main",
            "status": "Active",
            "client_email": email,
            "login_type": "client",
            "created_by": current_user_email(),
            "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        })

        save_json(USERS_FILE, users_data)

        add_audit("Created", "Client", company, email, "0")

        flash("Client and login password created successfully.", "success")
        return redirect(url_for("superadmin.clients"))

    return render_template(
        "superadmin/clients.html",
        clients=clients_data,
        plans=plans_data
    )


@superadmin_bp.route("/superadmin/plans", methods=["GET", "POST"])
@login_required
@superadmin_required
def plans():
    plans_data = load_json(PLANS_FILE)

    if not plans_data:
        plans_data = default_plans()
        save_json(PLANS_FILE, plans_data)

    if request.method == "POST":
        plan_id = request.form.get("plan_id", "").strip()

        plan_record = {
            "id": plan_id or uuid.uuid4().hex,
            "plan": request.form.get("plan", "").strip(),
            "price": request.form.get("price", "0").strip(),
            "user_limit": request.form.get("user_limit", "1").strip(),
            "branch_limit": request.form.get("branch_limit", "1").strip(),
            "invoice_limit": request.form.get("invoice_limit", "100").strip(),
            "validity_days": request.form.get("validity_days", "365").strip(),
            "status": request.form.get("status", "Active").strip(),
            "updated_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        }

        if not plan_record["plan"]:
            flash("Plan name is required.", "error")
            return redirect(url_for("superadmin.plans"))

        plans_data = [
            p for p in plans_data
            if p.get("id") != plan_record["id"]
        ]

        plans_data.insert(0, plan_record)
        save_json(PLANS_FILE, plans_data)

        flash("Plan saved successfully.", "success")
        return redirect(url_for("superadmin.plans"))

    return render_template(
        "superadmin/plans.html",
        plans=plans_data
    )


@superadmin_bp.route("/superadmin/updates", methods=["GET", "POST"])
@login_required
@superadmin_required
def updates():
    updates_data = load_json(UPDATES_FILE)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        status = request.form.get("status", "Published")
        image_url = ""

        image = request.files.get("image")

        if image and image.filename:
            ext = image.filename.rsplit(".", 1)[-1].lower()

            if ext in ALLOWED_EXT:
                filename = secure_filename(
                    f"{uuid.uuid4().hex}_{image.filename}"
                )

                image.save(
                    os.path.join(
                        current_app.config["UPLOAD_FOLDER"],
                        filename
                    )
                )

                image_url = f"/data-file/{filename}"

        if title and message:
            updates_data.insert(0, {
                "id": uuid.uuid4().hex,
                "title": title,
                "message": message,
                "status": status,
                "image_url": image_url,
                "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
            })

            save_json(UPDATES_FILE, updates_data)
            flash("Update published successfully.", "success")
        else:
            flash("Title and message are required.", "error")

        return redirect(url_for("superadmin.updates"))

    return render_template(
        "superadmin/updates.html",
        updates=updates_data
    )


@superadmin_bp.route("/client-data")
@login_required
@superadmin_required
def client_data():
    clients_data = load_json(CLIENTS_FILE)
    return render_template(
        "superadmin/client_data.html",
        clients=clients_data
    )


@superadmin_bp.route("/audit")
@login_required
@superadmin_required
def audit():
    logs = load_json(AUDIT_FILE)
    return render_template(
        "superadmin/audit.html",
        logs=logs
    )


@superadmin_bp.route("/subscription")
@login_required
def subscription():
    clients_data = load_json(CLIENTS_FILE)

    if session.get("login_type") == "superadmin":
        subscriptions = clients_data
    else:
        current_email = current_user_email()
        subscriptions = [
            c for c in clients_data
            if c.get("email") == current_email
        ]

    return render_template(
        "superadmin/subscription.html",
        subscriptions=subscriptions
    )


@superadmin_bp.route("/updates")
@login_required
def client_updates():
    updates_data = load_json(UPDATES_FILE)
    published = [
        u for u in updates_data
        if u.get("status") == "Published"
    ]

    return render_template(
        "client/updates.html",
        updates=published
    )
