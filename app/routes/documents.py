from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from .auth import login_required
import os, json, uuid
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


def is_superadmin():
    return session.get("login_type") == "superadmin" or session.get("role") == "superadmin"


def visible_data(data):
    if is_superadmin():
        return data
    return [d for d in data if d.get("client_email") == current_user_email()]


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
        "invoice_id": invoice["id"],
        "invoice_no": invoice["invoice_no"],
        "customer_name": invoice["customer_name"],
        "debit": invoice["grand_total"],
        "credit": "0",
        "amount": invoice["grand_total"],
        "type": "Invoice",
        "status": invoice["status"],
        "client_email": invoice["client_email"],
        "created_at": invoice["created_at"]
    })

    gst.insert(0, {
        "id": uuid.uuid4().hex,
        "invoice_id": invoice["id"],
        "invoice_no": invoice["invoice_no"],
        "customer_name": invoice["customer_name"],
        "taxable_amount": invoice["taxable_amount"],
        "cgst": invoice["cgst"],
        "sgst": invoice["sgst"],
        "igst": invoice["igst"],
        "total_gst": invoice["total_gst"],
        "grand_total": invoice["grand_total"],
        "status": invoice["status"],
        "client_email": invoice["client_email"],
        "created_at": invoice["created_at"]
    })

    tally.insert(0, {
        "id": uuid.uuid4().hex,
        "invoice_id": invoice["id"],
        "voucher_no": invoice["invoice_no"],
        "voucher_type": "Sales",
        "customer_name": invoice["customer_name"],
        "amount": invoice["grand_total"],
        "status": invoice["status"],
        "client_email": invoice["client_email"],
        "created_at": invoice["created_at"]
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
        "invoice_no": credit_note["credit_note_no"],
        "customer_name": inv.get("customer_name"),
        "debit": "0",
        "credit": inv.get("grand_total"),
        "amount": inv.get("grand_total"),
        "type": "Credit Note",
        "status": "Created",
        "client_email": inv.get("client_email"),
        "created_at": credit_note["created_at"]
    })

    gst.insert(0, {
        "id": uuid.uuid4().hex,
        "invoice_id": inv.get("id"),
        "invoice_no": credit_note["credit_note_no"],
        "customer_name": inv.get("customer_name"),
        "taxable_amount": "-" + str(inv.get("taxable_amount", "0")),
        "cgst": "-" + str(inv.get("cgst", "0")),
        "sgst": "-" + str(inv.get("sgst", "0")),
        "igst": "-" + str(inv.get("igst", "0")),
        "total_gst": "-" + str(inv.get("total_gst", "0")),
        "grand_total": "-" + str(inv.get("grand_total", "0")),
        "status": "Credit Note",
        "client_email": inv.get("client_email"),
        "created_at": credit_note["created_at"]
    })

    tally.insert(0, {
        "id": uuid.uuid4().hex,
        "invoice_id": inv.get("id"),
        "voucher_no": credit_note["credit_note_no"],
        "voucher_type": "Credit Note",
        "customer_name": inv.get("customer_name"),
        "amount": "-" + str(inv.get("grand_total", "0")),
        "status": "Created",
        "client_email": inv.get("client_email"),
        "created_at": credit_note["created_at"]
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
                    "product_name": product_names[i],
                    "description": descriptions[i] if i < len(descriptions) else "",
                    "hsn_code": hsn_codes[i] if i < len(hsn_codes) else "",
                    "unit": units[i] if i < len(units) else "",
                    "qty": qtys[i] if i < len(qtys) else "1",
                    "rate": rates[i] if i < len(rates) else "0",
                    "discount": discounts[i] if i < len(discounts) else "0",
                    "gst_percent": gst_percents[i] if i < len(gst_percents) else "0",
                    "cgst": cgsts[i] if i < len(cgsts) else "0",
                    "sgst": sgsts[i] if i < len(sgsts) else "0",
                    "igst": igsts[i] if i < len(igsts) else "0",
                    "line_total": totals[i] if i < len(totals) else "0"
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

        flash("Invoice saved and posted to Ledger, GST and Tally/SAP.", "success")
        return redirect(url_for("documents.invoice_register"))

    return render_template(
        "documents/invoice.html",
        customers=customers,
        contracts=contracts,
        doc_no=generate_doc_no("INV", invoices)
    )


@documents_bp.route("/invoice-register")
@login_required
def invoice_register():
    invoices = visible_data(load_json(INVOICE_FILE))
    return render_template("documents/invoice_register.html", invoices=invoices)


@documents_bp.route("/invoice/preview/<invoice_id>")
@login_required
def invoice_preview(invoice_id):
    invoice_data = next(
        (i for i in visible_data(load_json(INVOICE_FILE)) if i.get("id") == invoice_id),
        None
    )

    if not invoice_data:
        return "Invoice not found", 404

    client_profile = get_client_profile(invoice_data.get("client_email", ""))

    return render_template(
        "documents/invoice_preview.html",
        invoice=invoice_data,
        client_profile=client_profile
    )


@documents_bp.route("/invoice/cancel/<invoice_id>", methods=["POST"])
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

            receipts_data.insert(0, {
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
            })

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
                "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
            })

            save_json(RECEIPT_FILE, receipts_data)
            save_json(LEDGER_FILE, ledger)
            flash("Receipt saved successfully and posted to ledger.", "success")

        return redirect(url_for("documents.receipts"))

    return render_template(
        "documents/payment_receipts.html",
        receipts=visible_data(receipts_data),
        invoices=invoices
    )


@documents_bp.route("/document-register")
@login_required
def document_register():
    invoices = visible_data(load_json(INVOICE_FILE))
    credit_notes = visible_data(load_json(CREDIT_NOTE_FILE))
    receipts_data = visible_data(load_json(RECEIPT_FILE))

    return render_template(
        "documents/register.html",
        invoices=invoices,
        credit_notes=credit_notes,
        receipts=receipts_data
    )
