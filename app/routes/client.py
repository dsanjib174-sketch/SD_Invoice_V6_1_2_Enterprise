from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename
from .auth import login_required
import os, json, uuid

client_bp = Blueprint("client", __name__)

PROFILE_FILE = "client_profiles.json"
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}


def _json_path(filename):
    return os.path.join(current_app.config["UPLOAD_FOLDER"], filename)


def load_json(filename):
    path = _json_path(filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    os.makedirs(os.path.dirname(_json_path(filename)), exist_ok=True)
    with open(_json_path(filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def current_user_email():
    return session.get("user") or session.get("email") or ""


@client_bp.route("/company-profile", methods=["GET", "POST"])
@login_required
def company_profile():
    profiles = load_json(PROFILE_FILE)
    user_email = current_user_email()

    profile = next((p for p in profiles if p.get("client_email") == user_email), None)

    if request.method == "POST":
        logo_url = profile.get("logo_url", "") if profile else ""

        logo = request.files.get("logo")
        if logo and logo.filename:
            ext = logo.filename.rsplit(".", 1)[-1].lower()
            if ext in ALLOWED_EXT:
                filename = secure_filename(f"{uuid.uuid4().hex}_{logo.filename}")
                logo_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                logo.save(logo_path)
                logo_url = f"/data-file/{filename}"

        data = {
            "client_email": user_email,
            "company_name": request.form.get("company_name", "").strip(),
            "gst_number": request.form.get("gst_number", "").strip(),
            "pan_number": request.form.get("pan_number", "").strip(),
            "address": request.form.get("address", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "email": request.form.get("email", "").strip(),
            "state": request.form.get("state", "").strip(),
            "bank_name": request.form.get("bank_name", "").strip(),
            "account_number": request.form.get("account_number", "").strip(),
            "ifsc_code": request.form.get("ifsc_code", "").strip(),
            "account_holder": request.form.get("account_holder", "").strip(),
            "terms": request.form.get("terms", "").strip(),
            "logo_url": logo_url
        }

        profiles = [p for p in profiles if p.get("client_email") != user_email]
        profiles.insert(0, data)
        save_json(PROFILE_FILE, profiles)

        flash("Company profile updated successfully.", "success")
        return redirect(url_for("client.company_profile"))

    return render_template("client/company_profile.html", profile=profile or {})
