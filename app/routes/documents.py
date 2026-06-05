from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from .auth import login_required
import os
import json
import uuid
from datetime import datetime

documents_bp = Blueprint("documents", __name__)

INVOICE_FILE = "invoices.json"
ROC_FILE = "rate_contracts.json"
LEDGER_FILE = "ledger.json"
GST_FILE = "gst_reports.json"
TALLY_FILE = "tally_exports.json"
CREDIT_NOTE_FILE = "credit_notes.json"
RECEIPT_FILE = "receipts.json"
PROFILE_FILE = "client_profiles.json"
DELIVERY_CHALLAN_FILE = "delivery_challans.json"
AUDIT_FILE = "audit_logs.json"


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


def is_superadmin():
    return session.get("login_type") == "superadmin" or session.get("role") == "superadmin"


def visible_data(data):
    if is_superadmin():
        return data
    return [d for d in data if d.get("client_email") == current_user_email()]


def add_audit(action, document_type, document_no, customer_name="", amount="0", client_email=None):
    logs = load_json(AUDIT_FILE)
    logs.insert(0, {
        "id": uuid.uuid4().hex,
        "action": action,
        "document_type": document_type,
        "document_no": document_no,
        "customer_name": customer_name,
        "amount": amount,
        "client_email": client_email or current_user_email(),
        "created_by": current_user_email(),
        "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
    })
    save_json(AUDIT_FILE, logs)


def get_client_profile(client_email):
    profiles = load_json(PROFILE_FILE)
    return next((p for p in profiles if p.get("client_email") == client_email), {})


def get_financial_year():
    today = datetime.now()
    y = today.year
    if today.month >= 4:
        return f"{str(y)[-2:]}-{str(y + 1)[-2:]}"
    return f"{str(y - 1)[-2:]}-{str(y)[-2:]}"


def generate_doc_no(prefix, records):
    return f"SD/{prefix}/{get_financial_year()}/{str(len(records) + 1).zfill(3)}"


def get_customers_from_roc():
    contracts = visible_data(load_json(ROC_FILE))
    return sorted(set([
        c.get("customer_name")
        for c in contracts
        if c.get("customer_name") and c.get("status") == "Active"
    ]))


def post_invoice(invoice):
    ledger = load_json(LEDGER_FILE)
    gst = load_json(GST_FILE)
    tally = load_json(TALLY_FILE)

    ledger.insert(0, {
        "id": uuid.uuid4().hex,
        "invoice_id": invoice.get("id"),
        "invoice_no": invoice.get("invoice_no"),
        "customer_name": invoice.get("customer_name"),
        "debit": invoice.get("grand_total", "0"),
        "credit": "0",
        "amount": invoice.get("grand_total", "0"),
        "type": "Invoice",
        "status": invoice.get("status", "Generated"),
        "client_email": invoice.get("client_email"),
        "created_at": invoice.get("created_at")
    })

    gst.insert(0, {
        "id": uuid.uuid4().hex,
        "invoice_id": invoice.get("id"),
        "invoice_no": invoice.get("invoice_no"),
        "customer_name": invoice.get("customer_name"),
        "taxable_amount": invoice.get("taxable_amount", "0"),
        "cgst": invoice.get("cgst", "0"),
        "sgst": invoice.get("sgst", "0"),
        "igst": invoice.get("igst", "0"),
        "total_gst": invoice.get("total_gst", "0"),
        "grand_total": invoice.get("grand_total", "0"),
        "status": invoice.get("status", "Generated"),
        "client_email": invoice.get("client_email"),
        "created_at": invoice.get("created_at")
    })

    tally.insert(0, {
        "id": uuid.uuid4().hex,
        "invoice_id": invoice.get("id"),
        "voucher_no": invoice.get("invoice_no"),
        "voucher_type": "Sales",
        "customer_name": invoice.get("customer_name"),
        "amount": invoice.get("grand_total", "0"),
        "status": invoice.get("status", "Generated"),
        "client_email": invoice.get("client_email"),
        "created_at": invoice.get("created_at")
    })

    save_json(LEDGER_FILE, ledger)
    save_json(GST_FILE, gst)
    save_json(TALLY_FILE, tally)


def reverse_invoice(inv, credit_note):
    ledger = load_json(LEDGER_FILE)
    gst = load_json(GST_FILE)
    tally = load_json(TALLY_FILE)

    ledger.insert(0, {
        "id": uuid.uuid4().hex,
        "invoice_id": inv.get("id"),
        "invoice_no": credit_note.get("credit_note_no"),
        "customer_name": inv.get("customer_name"),
        "debit": "0",
        "credit": inv.get("grand_total", "0"),
        "amount": inv.get("grand_total", "0"),
        "type": "Credit Note",
        "status": "Created",
        "client_email": inv.get("client_email"),
        "created_at": credit_note.get("created_at")
    })

    gst.insert(0, {
        "id": uuid.uuid4().hex,
        "invoice_id": inv.get("id"),
        "invoice_no": credit_note.get("credit_note_no"),
        "customer_name": inv.get("customer_name"),
        "taxable_amount": "-" + str(inv.get("taxable_amount", "0")),
        "cgst": "-" + str(inv.get("cgst", "0")),
        "sgst": "-" + str(inv.get("sgst", "0")),
        "igst": "-" + str(inv.get("igst", "0")),
        "total_gst": "-" + str(inv.get("total_gst", "0")),
        "grand_total": "-" + str(inv.get("grand_total", "0")),
        "status": "Credit Note",
        "client_email": inv.get("client_email"),
        "created_at": credit_note.get("created_at")
    })

    tally.insert(0, {
        "id": uuid.uuid4().hex,
        "invoice_id": inv.get("id"),
        "voucher_no": credit_note.get("credit_note_no"),
        "voucher_type": "Credit Note",
        "customer_name": inv.get("customer_name"),
        "amount": "-" + str(inv.get("grand_total", "0")),
        "status": "Created",
        "client_email": inv.get("client_email"),
        "created_at": credit_note.get("created_at")
    })

    save_json(LEDGER_FILE, ledger)
    save_json(GST_FILE, gst)
    save_json(TALLY_FILE, tally)


@documents_bp.route("/invoice", methods=["GET", "POST"])
@login_required
def invoice():
    invoices = load_json(INVOICE_FILE)
    contracts = visible_data(load_json(ROC_FILE))
    customers = get_customers_from_roc()
    user_email = current_user_email()

    if request.method == "POST":
        invoice_no = request.form.get("invoice_no", "").strip() or generate_doc_no("INV", invoices)

        product_names = request.form.getlist("product_name[]")
        descriptions = request.form.getlist("description[]")
        hsn_codes = request.form.getlist("hsn_code[]")
        units = request.form.getlist("unit[]")
        qtys = request.form.getlist("qty[]")
        rates = request.form.getlist("rate[]")
        discounts = request.form.getlist("discount[]")
        gst_percents = request.form.getlist("gst_percent[]")
        cgsts = request.form.getlist("cgst[]")
        sgsts = request.form.getlist("sgst[]")
        igsts = request.form.getlist("igst[]")
        totals = request.form.getlist("line_total[]")

        items = []
        for i in range(len(product_names)):
            if product_names[i].strip():
                items.append({
                    "product_name": product_names[i].strip(),
                    "description": descriptions[i].strip() if i < len(descriptions) else "",
                    "hsn_code": hsn_codes[i].strip() if i < len(hsn_codes) else "",
                    "unit": units[i].strip() if i < len(units) else "",
                    "qty": qtys[i].strip() if i < len(qtys) else "1",
                    "rate": rates[i].strip() if i < len(rates) else "0",
                    "discount": discounts[i].strip() if i < len(discounts) else "0",
                    "gst_percent": gst_percents[i].strip() if i < len(gst_percents) else "0",
                    "cgst": cgsts[i].strip() if i < len(cgsts) else "0",
                    "sgst": sgsts[i].strip() if i < len(sgsts) else "0",
                    "igst": igsts[i].strip() if i < len(igsts) else "0",
                    "line_total": totals[i].strip() if i < len(totals) else "0"
                })

        if not items:
            flash("Please add at least one line item.", "error")
            return redirect(url_for("documents.invoice"))

        invoice_data = {
            "id": uuid.uuid4().hex,
            "invoice_no": invoice_no,
            "document_date": request.form.get("document_date", ""),
            "due_date": request.form.get("due_date", ""),
            "po_number": request.form.get("po_number", ""),
            "po_date": request.form.get("po_date", ""),
            "place_of_supply": request.form.get("place_of_supply", ""),
            "payment_terms": request.form.get("payment_terms", ""),
            "customer_name": request.form.get("customer_name", ""),
            "customer_gst": request.form.get("customer_gst", ""),
            "customer_pan": request.form.get("customer_pan", ""),
            "customer_email": request.form.get("customer_email", ""),
            "customer_mobile": request.form.get("customer_mobile", ""),
            "customer_address": request.form.get("customer_address", ""),
            "shipping_address": request.form.get("shipping_address", ""),
            "items": items,
            "taxable_amount": request.form.get("taxable_amount", "0"),
            "cgst": request.form.get("cgst_total", "0"),
            "sgst": request.form.get("sgst_total", "0"),
            "igst": request.form.get("igst_total", "0"),
            "total_gst": request.form.get("total_gst", "0"),
            "round_off": request.form.get("round_off", "0"),
            "grand_total": request.form.get("grand_total", "0"),
            "amount_words": request.form.get("amount_words", ""),
            "terms": request.form.get("terms", ""),
            "notes": request.form.get("notes", ""),
            "status": "Generated",
            "client_email": user_email,
            "created_by": user_email,
            "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        }

        invoices.insert(0, invoice_data)
        save_json(INVOICE_FILE, invoices)
        post_invoice(invoice_data)
        add_audit("Created", "Invoice", invoice_no, invoice_data["customer_name"], invoice_data["grand_total"], user_email)

        flash("Invoice saved and posted to Ledger, GST and Tally/SAP.", "success")
        return redirect(url_for("documents.invoice_register"))

    return render_template("documents/invoice.html", customers=customers, contracts=contracts, doc_no=generate_doc_no("INV", invoices))


@documents_bp.route("/invoice-register")
@login_required
def invoice_register():
    invoices = visible_data(load_json(INVOICE_FILE))
    return render_template("documents/invoice_register.html", invoices=invoices)


@documents_bp.route("/invoice/preview/<string:invoice_id>")
@login_required
def invoice_preview(invoice_id):
    invoice_data = next((i for i in visible_data(load_json(INVOICE_FILE)) if i.get("id") == invoice_id), None)
    if not invoice_data:
        return "Invoice not found", 404

    client_profile = get_client_profile(invoice_data.get("client_email", ""))

    return render_template("documents/invoice_preview.html", invoice=invoice_data, client_profile=client_profile)


@documents_bp.route("/invoice/cancel/<string:invoice_id>", methods=["POST"])
@login_required
def cancel_invoice(invoice_id):
    invoices = load_json(INVOICE_FILE)
    credit_notes = load_json(CREDIT_NOTE_FILE)
    user_email = current_user_email()

    for inv in invoices:
        if inv.get("id") == invoice_id:
            if not is_superadmin() and inv.get("client_email") != user_email:
                flash("You cannot cancel another client's invoice.", "error")
                return redirect(url_for("documents.invoice_register"))

            if inv.get("status") == "Cancelled":
                flash("Invoice already cancelled.", "error")
                return redirect(url_for("documents.invoice_register"))

            reason = request.form.get("cancel_reason", "").strip() or "Invoice cancelled"

            inv["status"] = "Cancelled"
            inv["cancel_reason"] = reason
            inv["cancelled_at"] = datetime.now().strftime("%d-%m-%Y %I:%M %p")

            credit_note = {
                "id": uuid.uuid4().hex,
                "credit_note_no": generate_doc_no("CN", credit_notes),
                "invoice_id": inv.get("id"),
                "invoice_no": inv.get("invoice_no"),
                "customer_name": inv.get("customer_name"),
                "amount": inv.get("grand_total"),
                "reason": reason,
                "status": "Created",
                "client_email": inv.get("client_email"),
                "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
            }

            credit_notes.insert(0, credit_note)
            reverse_invoice(inv, credit_note)
            add_audit("Cancelled", "Invoice", inv.get("invoice_no"), inv.get("customer_name"), inv.get("grand_total"), inv.get("client_email"))
            add_audit("Created", "Credit Note", credit_note["credit_note_no"], credit_note["customer_name"], credit_note["amount"], credit_note["client_email"])
            break

    save_json(INVOICE_FILE, invoices)
    save_json(CREDIT_NOTE_FILE, credit_notes)

    flash("Invoice cancelled, credit note created and reverse entries posted.", "success")
    return redirect(url_for("documents.invoice_register"))


@documents_bp.route("/credit-note")
@login_required
def credit_note():
    notes = visible_data(load_json(CREDIT_NOTE_FILE))
    return render_template("documents/credit_note.html", notes=notes)


@documents_bp.route("/credit-note/preview/<string:note_id>")
@login_required
def credit_note_preview(note_id):
    note = next((n for n in visible_data(load_json(CREDIT_NOTE_FILE)) if n.get("id") == note_id), None)
    if not note:
        return "Credit note not found", 404
    return render_template("documents/credit_note_preview.html", note=note)


@documents_bp.route("/receipts", methods=["GET", "POST"])
@login_required
def receipts():
    receipts_data = load_json(RECEIPT_FILE)
    invoices = visible_data(load_json(INVOICE_FILE))
    user_email = current_user_email()

    if request.method == "POST":
        invoice_id = request.form.get("invoice_id")
        invoice_data = next((i for i in invoices if i.get("id") == invoice_id), None)

        if invoice_data:
            amount_received = request.form.get("amount_received", "0")

            receipt = {
                "id": uuid.uuid4().hex,
                "receipt_no": generate_doc_no("RCPT", receipts_data),
                "invoice_id": invoice_data.get("id"),
                "invoice_no": invoice_data.get("invoice_no"),
                "customer_name": invoice_data.get("customer_name"),
                "amount_received": amount_received,
                "payment_mode": request.form.get("payment_mode", ""),
                "payment_date": request.form.get("payment_date", ""),
                "remarks": request.form.get("remarks", ""),
                "client_email": user_email,
                "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
            }

            receipts_data.insert(0, receipt)

            ledger = load_json(LEDGER_FILE)
            ledger.insert(0, {
                "id": uuid.uuid4().hex,
                "invoice_no": invoice_data.get("invoice_no"),
                "customer_name": invoice_data.get("customer_name"),
                "debit": "0",
                "credit": amount_received,
                "amount": amount_received,
                "type": "Receipt",
                "status": "Received",
                "client_email": user_email,
                "created_at": receipt["created_at"]
            })

            save_json(RECEIPT_FILE, receipts_data)
            save_json(LEDGER_FILE, ledger)
            add_audit("Created", "Receipt", receipt["receipt_no"], receipt["customer_name"], amount_received, user_email)

            flash("Receipt saved successfully and posted to ledger.", "success")

        return redirect(url_for("documents.receipts"))

    return render_template("documents/payment_receipts.html", receipts=visible_data(receipts_data), invoices=invoices)


@documents_bp.route("/delivery-challan", methods=["GET", "POST"])
@login_required
def delivery_challan():
    challans = load_json(DELIVERY_CHALLAN_FILE)
    customers = get_customers_from_roc()
    contracts = visible_data(load_json(ROC_FILE))

    if request.method == "POST":
        product_names = request.form.getlist("product_name[]")
        qtys = request.form.getlist("qty[]")
        units = request.form.getlist("unit[]")
        remarks_list = request.form.getlist("item_remarks[]")

        items = []
        for i in range(len(product_names)):
            if product_names[i].strip():
                items.append({
                    "product_name": product_names[i].strip(),
                    "qty": qtys[i].strip() if i < len(qtys) else "",
                    "unit": units[i].strip() if i < len(units) else "",
                    "remarks": remarks_list[i].strip() if i < len(remarks_list) else ""
                })

        challan_no = request.form.get("challan_no", "").strip() or generate_doc_no("DC", challans)

        challan = {
            "id": uuid.uuid4().hex,
            "challan_no": challan_no,
            "customer_name": request.form.get("customer_name", "").strip(),
            "delivery_date": request.form.get("delivery_date", "").strip(),
            "vehicle_no": request.form.get("vehicle_no", "").strip(),
            "delivery_address": request.form.get("delivery_address", "").strip(),
            "remarks": request.form.get("remarks", "").strip(),
            "items": items,
            "status": "Generated",
            "client_email": current_user_email(),
            "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        }

        challans.insert(0, challan)
        save_json(DELIVERY_CHALLAN_FILE, challans)
        add_audit("Created", "Delivery Challan", challan_no, challan["customer_name"], "0", challan["client_email"])

        flash("Delivery Challan saved successfully.", "success")
        return redirect(url_for("documents.delivery_challan"))

    return render_template("documents/delivery_challan.html", challans=visible_data(challans), customers=customers, contracts=contracts, doc_no=generate_doc_no("DC", challans))


@documents_bp.route("/document-register")
@login_required
def document_register():
    invoices = visible_data(load_json(INVOICE_FILE))
    credit_notes = visible_data(load_json(CREDIT_NOTE_FILE))
    receipts_data = visible_data(load_json(RECEIPT_FILE))
    challans = visible_data(load_json(DELIVERY_CHALLAN_FILE))

    return render_template("documents/register.html", invoices=invoices, credit_notes=credit_notes, receipts=receipts_data, challans=challans)
