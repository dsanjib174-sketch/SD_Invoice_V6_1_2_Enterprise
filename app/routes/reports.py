from flask import Blueprint, current_app, session, Response, render_template_string
from .auth import login_required
import os, json, csv, io

reports_bp = Blueprint("reports", __name__)

GST_FILE = "gst_reports.json"


def _json_path(filename):
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
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


def current_user_email():
    return session.get("user") or session.get("email") or ""


def is_superadmin():
    return session.get("login_type") == "superadmin" or session.get("role") == "superadmin"


def visible_data(data):
    if is_superadmin():
        return data
    return [d for d in data if d.get("client_email") == current_user_email()]


GST_PAGE = """
{% extends "base.html" %}
{% block content %}
<section>
<h2>GST/GSP Reports</h2>

<a href="/gst/export"><button type="button">Export GSTR-1 CSV</button></a>
<br><br>

<table border="1" cellpadding="8" cellspacing="0" width="100%">
<tr>
<th>Invoice No</th>
<th>Customer</th>
<th>Taxable</th>
<th>CGST</th>
<th>SGST</th>
<th>IGST</th>
<th>Total GST</th>
<th>Grand Total</th>
<th>Status</th>
<th>Date</th>
</tr>

{% if records %}
{% for r in records %}
<tr>
<td>{{ r.get("invoice_no", "") }}</td>
<td>{{ r.get("customer_name", "") }}</td>
<td>{{ r.get("taxable_amount", "0") }}</td>
<td>{{ r.get("cgst", "0") }}</td>
<td>{{ r.get("sgst", "0") }}</td>
<td>{{ r.get("igst", "0") }}</td>
<td>{{ r.get("total_gst", "0") }}</td>
<td>{{ r.get("grand_total", "0") }}</td>
<td>{{ r.get("status", "") }}</td>
<td>{{ r.get("created_at", "") }}</td>
</tr>
{% endfor %}
{% else %}
<tr><td colspan="10">No records.</td></tr>
{% endif %}
</table>
</section>
{% endblock %}
"""


@reports_bp.route("/gst")
@reports_bp.route("/gst-gsp")
@login_required
def gst():
    records = visible_data(load_json(GST_FILE))
    return render_template_string(GST_PAGE, records=records)


@reports_bp.route("/gst/export")
@login_required
def gst_export():
    records = visible_data(load_json(GST_FILE))

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Invoice No", "Customer", "Taxable Amount", "CGST", "SGST",
        "IGST", "Total GST", "Grand Total", "Status", "Date"
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
