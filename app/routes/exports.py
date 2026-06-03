from flask import Blueprint, render_template, current_app, session, Response
from .auth import login_required
import os, json, csv, io

exports_bp = Blueprint("exports", __name__)

TALLY_FILE = "tally_exports.json"


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


@exports_bp.route("/tally-sap")
@login_required
def tally_sap():
    records = visible_data(load_json(TALLY_FILE))
    return render_template("exports/tally_sap.html", records=records)


@exports_bp.route("/tally/export")
@login_required
def tally_export():
    records = visible_data(load_json(TALLY_FILE))

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Voucher No",
        "Voucher Type",
        "Customer",
        "Amount",
        "Status",
        "Date"
    ])

    for r in records:
        writer.writerow([
            r.get("voucher_no", ""),
            r.get("voucher_type", ""),
            r.get("customer_name", ""),
            r.get("amount", ""),
            r.get("status", ""),
            r.get("created_at", "")
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=tally_export.csv"}
    )


@exports_bp.route("/sap/export")
@login_required
def sap_export():
    records = visible_data(load_json(TALLY_FILE))

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Document No",
        "Document Type",
        "Customer",
        "Amount",
        "Status",
        "Date"
    ])

    for r in records:
        writer.writerow([
            r.get("voucher_no", ""),
            r.get("voucher_type", ""),
            r.get("customer_name", ""),
            r.get("amount", ""),
            r.get("status", ""),
            r.get("created_at", "")
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sap_export.csv"}
    )
