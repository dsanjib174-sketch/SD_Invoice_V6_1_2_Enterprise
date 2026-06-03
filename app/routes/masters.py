from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from .auth import login_required
import os, json, uuid
from datetime import datetime

masters_bp = Blueprint("masters", __name__)

CUSTOMERS_FILE = "customers.json"
ROC_FILE = "rate_contracts.json"


def _json_path(filename):
    return os.path.join(current_app.config["UPLOAD_FOLDER"], filename)


def load_json(filename):
    path = _json_path(filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_json(filename, data):
    os.makedirs(os.path.dirname(_json_path(filename)), exist_ok=True)
    with open(_json_path(filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def current_user_email():
    return session.get("user") or session.get("email") or ""


def is_superadmin():
    return session.get("login_type") == "superadmin" or session.get("role") == "superadmin"


def visible(items):
    if is_superadmin():
        return items
    email = current_user_email()
    return [i for i in items if i.get("client_email") == email or i.get("created_by") == email]


@masters_bp.route("/masters")
@login_required
def masters():
    return render_template("masters/masters.html")


@masters_bp.route("/customer-master", methods=["GET", "POST"])
@login_required
def customer_master():
    customers = load_json(CUSTOMERS_FILE)
    user_email = current_user_email()
    if request.method == "POST":
        company_name = request.form.get("company_name", "").strip()
        if not company_name:
            flash("Company name is required.", "error")
            return redirect(url_for("masters.customer_master"))
        customers.insert(0, {
            "id": uuid.uuid4().hex,
            "company_name": company_name,
            "customer_email": request.form.get("customer_email", "").strip(),
            "customer_mobile": request.form.get("customer_mobile", "").strip(),
            "gst_number": request.form.get("gst_number", "").strip(),
            "pan_number": request.form.get("pan_number", "").strip(),
            "customer_address": request.form.get("customer_address", "").strip(),
            "client_email": user_email,
            "created_by": user_email,
            "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        })
        save_json(CUSTOMERS_FILE, customers)
        flash("Customer saved successfully.", "success")
        return redirect(url_for("masters.customer_master"))
    return render_template("masters/customer_master.html", customers=visible(customers))


@masters_bp.route("/product-master")
@login_required
def product_master():
    return render_template("masters/product_master.html")


@masters_bp.route("/rate-contract", methods=["GET", "POST"])
@login_required
def rate_contract():
    customers = visible(load_json(CUSTOMERS_FILE))
    contracts = load_json(ROC_FILE)
    user_email = current_user_email()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "save_contract":
            if not request.form.get("customer_name") or not request.form.get("product_name") or not request.form.get("rate"):
                flash("Customer, product/service and rate are required.", "error")
                return redirect(url_for("masters.rate_contract"))
            contracts.insert(0, {
                "id": uuid.uuid4().hex,
                "customer_name": request.form.get("customer_name", "").strip(),
                "customer_email": request.form.get("customer_email", "").strip(),
                "customer_mobile": request.form.get("customer_mobile", "").strip(),
                "customer_gst": request.form.get("customer_gst", "").strip(),
                "customer_pan": request.form.get("customer_pan", "").strip(),
                "customer_address": request.form.get("customer_address", "").strip(),
                "product_name": request.form.get("product_name", "").strip(),
                "hsn_code": request.form.get("hsn_code", "").strip(),
                "unit": request.form.get("unit", "").strip(),
                "rate": request.form.get("rate", "").strip(),
                "gst_percent": request.form.get("gst_percent", "").strip(),
                "valid_from": request.form.get("valid_from", "").strip(),
                "valid_to": request.form.get("valid_to", "").strip(),
                "remarks": request.form.get("remarks", "").strip(),
                "source": "Manual",
                "status": "Active",
                "client_email": user_email,
                "created_by": user_email,
                "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
            })
            save_json(ROC_FILE, contracts)
            flash("Rate contract saved successfully.", "success")
        elif action == "update_contract":
            cid = request.form.get("contract_id")
            for c in contracts:
                if c.get("id") == cid:
                    if not is_superadmin() and c.get("client_email") != user_email and c.get("created_by") != user_email:
                        flash("You cannot update another client's contract.", "error")
                        return redirect(url_for("masters.rate_contract"))
                    c.update({
                        "customer_name": request.form.get("customer_name", "").strip(),
                        "customer_email": request.form.get("customer_email", "").strip(),
                        "customer_mobile": request.form.get("customer_mobile", "").strip(),
                        "customer_gst": request.form.get("customer_gst", "").strip(),
                        "customer_pan": request.form.get("customer_pan", "").strip(),
                        "customer_address": request.form.get("customer_address", "").strip(),
                        "product_name": request.form.get("product_name", "").strip(),
                        "hsn_code": request.form.get("hsn_code", "").strip(),
                        "unit": request.form.get("unit", "").strip(),
                        "rate": request.form.get("rate", "").strip(),
                        "gst_percent": request.form.get("gst_percent", "").strip(),
                        "valid_from": request.form.get("valid_from", "").strip(),
                        "valid_to": request.form.get("valid_to", "").strip(),
                        "remarks": request.form.get("remarks", "").strip(),
                        "status": request.form.get("status", "Active").strip(),
                        "updated_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
                    })
                    break
            save_json(ROC_FILE, contracts)
            flash("Rate contract updated successfully.", "success")
        return redirect(url_for("masters.rate_contract"))
    return render_template("masters/rate_contract.html", customers=customers, contracts=visible(contracts))
