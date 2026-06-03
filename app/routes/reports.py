from flask import Blueprint, render_template, current_app, session, Response
from .auth import login_required
import os, json, csv, io

reports_bp = Blueprint("reports", __name__)

GST_FILE = "gst_reports.json"


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


@reports_bp.route("/gst-gsp")
@login_required
def gst_gsp():
    records = visible_data(load_json(GST_FILE))
    return render_template("reports/gst.html", records=records)


@reports_bp.route("/gst/export")
@login_required
def gst_export():
    records = visible_data(load_json(GST_FILE))

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Invoice No",
        "Customer",
        "Taxable Amount",
        "CGST",
        "SGST",
        "IGST",
        "Total GST",
        "Grand Total",
        "Status",
        "Date"
    ])

    for r in records:
        writer.writerow([
            r.get("invoice_no", ""),
            r.get("customer_name", ""),
            r.get("taxable_amount", ""),
            r.get("cgst", ""),
            r.get("sgst", ""),
            r.get("igst", ""),
            r.get("total_gst", ""),
            r.get("grand_total", ""),
            r.get("status", ""),
            r.get("created_at", "")
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=gstr_1.csv"}
    )
