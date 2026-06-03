from flask import Blueprint, render_template, current_app, session, Response
from .auth import login_required
import os, json, csv, io

reports_bp = Blueprint("reports", __name__)

INVOICE_FILE = "invoices.json"
QUOTATION_FILE = "quotations.json"
PROFORMA_FILE = "proformas.json"
DELIVERY_CHALLAN_FILE = "delivery_challans.json"
CREDIT_NOTE_FILE = "credit_notes.json"
LEDGER_FILE = "ledger_entries.json"
GST_FILE = "gst_entries.json"
TALLY_FILE = "tally_entries.json"


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


def is_superadmin():
    return session.get("login_type") == "superadmin" or session.get("role") == "superadmin"


def current_user_email():
    return session.get("user") or session.get("email") or ""


def visible(data):
    if is_superadmin():
        return data
    email = current_user_email()
    return [d for d in data if d.get("client_email") == email or d.get("created_by") == email]


def csv_response(filename, rows, headers):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({h: row.get(h, "") for h in headers})
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})


@reports_bp.route("/document-register")
@login_required
def document_register():
    docs = []
    for file_name, doc_type, no_field in [
        (QUOTATION_FILE, "Quotation", "quotation_no"),
        (PROFORMA_FILE, "Proforma", "proforma_no"),
        (INVOICE_FILE, "Invoice", "invoice_no"),
        (DELIVERY_CHALLAN_FILE, "Delivery Challan", "challan_no"),
        (CREDIT_NOTE_FILE, "Credit Note", "credit_note_no"),
    ]:
        for item in visible(load_json(file_name)):
            docs.append({
                "no": item.get(no_field, ""),
                "type": doc_type,
                "customer_name": item.get("customer_name", ""),
                "total": item.get("grand_total", item.get("amount", "0")),
                "status": item.get("status", "Generated"),
                "created_at": item.get("created_at", "")
            })
    return render_template("reports/document_register.html", docs=docs)


@reports_bp.route("/ledger")
@login_required
def ledger():
    entries = visible(load_json(LEDGER_FILE))
    return render_template("reports/ledger.html", entries=entries)


@reports_bp.route("/gst-gsp")
@login_required
def gst_gsp():
    entries = visible(load_json(GST_FILE))
    return render_template("reports/gst_gsp.html", entries=entries)


@reports_bp.route("/gst-gsp/export")
@login_required
def gst_gsp_export():
    entries = visible(load_json(GST_FILE))
    headers = ["document_no", "customer_name", "gstin", "taxable_amount", "cgst", "sgst", "igst", "total_gst", "grand_total"]
    return csv_response("gstr_1_export.csv", entries, headers)


@reports_bp.route("/tally-sap")
@login_required
def tally_sap():
    entries = visible(load_json(TALLY_FILE))
    return render_template("reports/tally_sap.html", entries=entries)


@reports_bp.route("/tally-sap/export")
@login_required
def tally_sap_export():
    entries = visible(load_json(TALLY_FILE))
    headers = ["voucher_type", "invoice_no", "party_name", "amount", "taxable_amount", "gst_amount", "created_at"]
    return csv_response("tally_sap_export.csv", entries, headers)
