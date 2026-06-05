from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    session,
    send_from_directory
)
from werkzeug.utils import secure_filename
from .auth import login_required
import os
import json
import uuid

client_bp = Blueprint("client", __name__)

PROFILE_FILE = "client_profiles.json"
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif"}


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


@client_bp.route("/company-profile", methods=["GET", "POST"])
@login_required
def company_profile():
    profiles = load_json(PROFILE_FILE)
    user_email = current_user_email()

    profile = next(
        (p for p in profiles if p.get("client_email") == user_email),
        None
    )

    if request.method == "POST":
        logo_url = profile.get("logo_url", "") if profile else ""

        logo = request.files.get("logo")

        if logo and logo.filename:
            ext = logo.filename.rsplit(".", 1)[-1].lower()

            if ext in ALLOWED_EXT:
                safe_name = secure_filename(logo.filename)
                filename = f"{uuid.uuid4().hex}_{safe_name}"

                logo_path = os.path.join(
                    current_app.config["UPLOAD_FOLDER"],
                    filename
                )

                os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
                logo.save(logo_path)

                logo_url = f"/data-file/{filename}"
            else:
                flash("Invalid logo file type. Use PNG, JPG, JPEG, WEBP or GIF.", "error")
                return redirect(url_for("client.company_profile"))

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

        profiles = [
            p for p in profiles
            if p.get("client_email") != user_email
        ]

        profiles.insert(0, data)
        save_json(PROFILE_FILE, profiles)

        flash("Company profile updated successfully.", "success")
        return redirect(url_for("client.company_profile"))

    return render_template(
        "client/company_profile.html",
        profile=profile or {}
    )


@client_bp.route("/data-file/<path:filename>")
@login_required
def data_file(filename):
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )
