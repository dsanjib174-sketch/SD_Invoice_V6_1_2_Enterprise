from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, session
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os, json, uuid
from .auth import login_required, superadmin_required

superadmin_bp = Blueprint("superadmin", __name__)
DATA_FILE = "updates.json"
CLIENTS_FILE = "clients.json"
PLANS_FILE = "plans.json"
SUBSCRIPTIONS_FILE = "subscriptions.json"
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


def _json_path(filename):
    return os.path.join(current_app.config["UPLOAD_FOLDER"], filename)


def load_json(path, default_value):
    if not os.path.exists(path):
        return default_value
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def load_updates(): return load_json(_json_path(DATA_FILE), [])
def save_updates(items): save_json(_json_path(DATA_FILE), items)
def load_clients(): return load_json(_json_path(CLIENTS_FILE), [])
def save_clients(items): save_json(_json_path(CLIENTS_FILE), items)
def load_subscriptions(): return load_json(_json_path(SUBSCRIPTIONS_FILE), [])
def save_subscriptions(items): save_json(_json_path(SUBSCRIPTIONS_FILE), items)


def default_plans():
    return [
        {"id": uuid.uuid4().hex, "plan": "Basic", "price": "4999", "user_limit": "2", "branch_limit": "1", "invoice_limit": "100", "validity_years": "1", "status": "Active"},
        {"id": uuid.uuid4().hex, "plan": "Standard", "price": "9999", "user_limit": "5", "branch_limit": "3", "invoice_limit": "500", "validity_years": "1", "status": "Active"},
        {"id": uuid.uuid4().hex, "plan": "Premium", "price": "19999", "user_limit": "10", "branch_limit": "10", "invoice_limit": "2000", "validity_years": "1", "status": "Active"},
        {"id": uuid.uuid4().hex, "plan": "Enterprise", "price": "49999", "user_limit": "Unlimited", "branch_limit": "Unlimited", "invoice_limit": "Unlimited", "validity_years": "1", "status": "Active"}
    ]


def load_plans():
    path = _json_path(PLANS_FILE)
    if not os.path.exists(path):
        plans = default_plans()
        save_plans(plans)
        return plans
    return load_json(path, [])


def save_plans(items): save_json(_json_path(PLANS_FILE), items)


def get_current_user_email(): return session.get("email") or session.get("user") or session.get("username") or ""
def is_superadmin_user(): return session.get("role") == "superadmin" or session.get("login_type") == "superadmin"


@superadmin_bp.route("/superadmin/clients", methods=["GET", "POST"])
@login_required
@superadmin_required
def clients():
    clients_data = load_clients()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            company = request.form.get("company", "").strip()
            email = request.form.get("email", "").strip()
            plan_name = request.form.get("plan_name", "").strip()
            active_date = datetime.today().date()
            expire_date = active_date + timedelta(days=365)
            if company and email and plan_name:
                clients_data.insert(0, {"id": uuid.uuid4().hex, "company": company, "email": email, "user_limit": request.form.get("user_limit", "").strip(), "branch_limit": request.form.get("branch_limit", "").strip(), "plan_name": plan_name, "active_date": active_date.strftime("%Y-%m-%d"), "expire_date": expire_date.strftime("%Y-%m-%d"), "expiry_edit_comment": "", "status": "Active", "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")})
                save_clients(clients_data); flash("Client created successfully.", "success")
            else:
                flash("Company, Email and Plan Name are required.", "error")
        elif action == "edit_expiry":
            client_id = request.form.get("client_id")
            new_date = request.form.get("new_expire_date")
            comment = request.form.get("comment", "").strip()
            if not new_date or not comment:
                flash("New expiry date and valid comment are required.", "error")
                return redirect(url_for("superadmin.clients"))
            for c in clients_data:
                if c.get("id") == client_id:
                    c["expire_date"] = new_date; c["expiry_edit_comment"] = comment; c["expiry_updated_at"] = datetime.now().strftime("%d-%m-%Y %I:%M %p"); break
            save_clients(clients_data); flash("Expiry date updated successfully.", "success")
        return redirect(url_for("superadmin.clients"))
    return render_template("superadmin/clients.html", clients=clients_data, plans=load_plans())


@superadmin_bp.route("/superadmin/plans", methods=["GET", "POST"])
@login_required
@superadmin_required
def plans():
    plans_data = load_plans()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            plans_data.insert(0, {"id": uuid.uuid4().hex, "plan": request.form.get("plan", "").strip(), "price": request.form.get("price", "").strip(), "user_limit": request.form.get("user_limit", "").strip(), "branch_limit": request.form.get("branch_limit", "").strip(), "invoice_limit": request.form.get("invoice_limit", "").strip(), "validity_years": "1", "status": "Active"})
            save_plans(plans_data); flash("Plan added successfully.", "success")
        elif action == "update":
            for p in plans_data:
                if p.get("id") == request.form.get("plan_id"):
                    p.update({"plan": request.form.get("plan", "").strip(), "price": request.form.get("price", "").strip(), "user_limit": request.form.get("user_limit", "").strip(), "branch_limit": request.form.get("branch_limit", "").strip(), "invoice_limit": request.form.get("invoice_limit", "").strip(), "validity_years": "1", "status": request.form.get("status", "Active")}); break
            save_plans(plans_data); flash("Plan updated successfully.", "success")
        return redirect(url_for("superadmin.plans"))
    return render_template("superadmin/plans.html", plans=plans_data)


@superadmin_bp.route("/superadmin/updates", methods=["GET", "POST"])
@login_required
@superadmin_required
def updates():
    if request.method == "POST":
        title = request.form.get("title", "").strip(); message = request.form.get("message", "").strip(); status = request.form.get("status", "Published")
        image_url = ""; image = request.files.get("image")
        if image and image.filename:
            ext = image.filename.rsplit(".", 1)[-1].lower()
            if ext in ALLOWED_EXT:
                filename = secure_filename(f"{uuid.uuid4().hex}_{image.filename}")
                folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "updates"); os.makedirs(folder, exist_ok=True)
                image.save(os.path.join(folder, filename)); image_url = f"/static/uploads/updates/{filename}"
            else:
                flash("Invalid image format.", "error"); return redirect(url_for("superadmin.updates"))
        if title and message:
            items = load_updates(); items.insert(0, {"id": uuid.uuid4().hex, "title": title, "message": message, "status": status, "image_url": image_url, "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")}); save_updates(items); flash("Update published successfully.", "success")
        else: flash("Title and message are required.", "error")
        return redirect(url_for("superadmin.updates"))
    return render_template("superadmin/updates.html", updates=load_updates())


@superadmin_bp.route("/updates")
@login_required
def client_updates():
    return render_template("client/updates.html", updates=[u for u in load_updates() if u.get("status") == "Published"])


@superadmin_bp.route("/client-data")
@login_required
@superadmin_required
def client_data(): return render_template("superadmin/client_data.html")


@superadmin_bp.route("/subscription", methods=["GET", "POST"])
@login_required
def subscription():
    subscriptions = load_subscriptions(); clients_data = load_clients(); user_email = get_current_user_email()
    if request.method == "POST":
        if not is_superadmin_user():
            flash("Only Super Admin can generate subscription invoices.", "error"); return redirect(url_for("superadmin.subscription"))
        if request.form.get("action") == "create_invoice":
            selected = next((c for c in clients_data if c.get("id") == request.form.get("client_id")), None)
            if selected:
                subscriptions.insert(0, {"id": uuid.uuid4().hex, "invoice_no": f"SUB-{datetime.now().strftime('%Y%m%d%H%M%S')}", "client_id": selected.get("id"), "client_company": selected.get("company"), "client_email": selected.get("email"), "plan_name": selected.get("plan_name"), "active_date": selected.get("active_date"), "expire_date": selected.get("expire_date"), "amount": request.form.get("amount", "0"), "status": "Generated", "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")})
                save_subscriptions(subscriptions); flash("Subscription invoice generated successfully.", "success")
            else: flash("Client not found.", "error")
        return redirect(url_for("superadmin.subscription"))
    visible = subscriptions if is_superadmin_user() else [s for s in subscriptions if s.get("client_email") == user_email]
    return render_template("superadmin/subscription.html", subscriptions=visible, clients=clients_data, user_email=user_email, is_superadmin=is_superadmin_user())


@superadmin_bp.route("/audit")
@login_required
@superadmin_required
def audit(): return render_template("superadmin/audit.html")
