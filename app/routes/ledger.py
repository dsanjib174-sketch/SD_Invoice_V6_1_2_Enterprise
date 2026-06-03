from flask import Blueprint, render_template, current_app, session
from .auth import login_required
import os, json

ledger_bp = Blueprint("ledger", __name__)

LEDGER_FILE = "ledger.json"


def _json_path(filename):
    return os.path.join(current_app.config["UPLOAD_FOLDER"], filename)


def load_json(filename):
    path = _json_path(filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def current_user_email():
    return session.get("user") or session.get("email") or ""


def is_superadmin():
    return session.get("login_type") == "superadmin" or session.get("role") == "superadmin"


def visible_data(data):
    if is_superadmin():
        return data
    return [d for d in data if d.get("client_email") == current_user_email()]


@ledger_bp.route("/ledger")
@login_required
def ledger():
    entries = visible_data(load_json(LEDGER_FILE))
    return render_template("ledger/ledger.html", entries=entries)
