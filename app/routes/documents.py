from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from .auth import login_required
import os, json, uuid
from datetime import datetime


documents_bp = Blueprint("documents", __name__)

QUOTATION_FILE = "quotations.json"
PROFORMA_FILE = "proformas.json"
INVOICE_FILE = "invoices.json"
DELIVERY_CHALLAN_FILE = "delivery_challans.json"
CREDIT_NOTE_FILE = "credit_notes.json"
ROC_FILE = "rate_contracts.json"
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
    email = current_user_email()
    return [d for d in data if d.get("client_email") == email or d.get("created_by") == email]


def get_financial_year():
    today = datetime.now()
    year = today.year
    if today.month >= 4:
        return f"{str(year)[-2:]}-{str(year + 1)[-2:]}"
    return f"{str(year - 1)[-2:]}-{str(year)[-2:]}"


def generate_doc_no(prefix, existing_docs):
    fy = get_financial_year()
    count = len(existing_docs) + 1
    return f"SD/{prefix}/{fy}/{str(count).zfill(3)}"


def load_roc():
    return load_json(ROC_FILE)


def active_contracts():
    return [c for c in visible_data(load_roc()) if c.get("status", "Active") == "Active"]


def get_customer_names():
    customers = sorted({c.get("customer_name", "") for c in active_contracts() if c.get("customer_name")})
    return customers


def safe_float(value):
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def collect_invoice_items():
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
    line_totals = request.form.getlist("line_total[]")
    items = []
    for i, product in enumerate(product_names):
        if not product.strip():
            continue
        qty = qtys[i] if i < len(qtys) else "1"
        rate = rates[i] if i < len(rates) else "0"
        discount = discounts[i] if i < len(discounts) else "0"
        gst_percent = gst_percents[i] if i < len(gst_percents) else "0"
        taxable = max((safe_float(qty) * safe_float(rate)) - safe_float(discount), 0)
        gst_amount = taxable * safe_float(gst_percent) / 100
        cgst = cgsts[i] if i < len(cgsts) and cgsts[i] else f"{gst_amount/2:.2f}"
        sgst = sgsts[i] if i < len(sgsts) and sgsts[i] else f"{gst_amount/2:.2f}"
        igst = igsts[i] if i < len(igsts) and igsts[i] else "0.00"
        line_total = line_totals[i] if i < len(line_totals) and line_totals[i] else f"{taxable+gst_amount:.2f}"
        items.append({
            "product_name": product.strip(),
            "description": descriptions[i].strip() if i < len(descriptions) else "",
            "hsn_code": hsn_codes[i].strip() if i < len(hsn_codes) else "",
            "unit": units[i].strip() if i < len(units) else "",
            "qty": qty.strip(),
            "rate": rate.strip(),
            "discount": discount.strip(),
            "gst_percent": gst_percent.strip(),
            "cgst": cgst.strip(),
            "sgst": sgst.strip(),
            "igst": igst.strip(),
            "line_total": line_total.strip()
        })
    return items


def make_invoice_record(invoice_no):
    items = collect_invoice_items()
    return {
        "id": uuid.uuid4().hex,
        "invoice_no": invoice_no,
        "document_date": request.form.get("document_date", "").strip(),
        "due_date": request.form.get("due_date", "").strip(),
        "po_number": request.form.get("po_number", "").strip(),
        "po_date": request.form.get("po_date", "").strip(),
        "place_of_supply": request.form.get("place_of_supply", "").strip(),
        "payment_terms": request.form.get("payment_terms", "").strip(),
        "customer_name": request.form.get("customer_name", "").strip(),
        "customer_gst": request.form.get("customer_gst", "").strip(),
        "customer_pan": request.form.get("customer_pan", "").strip(),
        "customer_email": request.form.get("customer_email", "").strip(),
        "customer_mobile": request.form.get("customer_mobile", "").strip(),
        "customer_address": request.form.get("customer_address", "").strip(),
        "shipping_address": request.form.get("shipping_address", "").strip(),
        "items": items,
        "taxable_amount": request.form.get("taxable_amount", "0").strip(),
        "cgst": request.form.get("cgst_total", "0").strip(),
        "sgst": request.form.get("sgst_total", "0").strip(),
        "igst": request.form.get("igst_total", "0").strip(),
        "total_gst": request.form.get("total_gst", "0").strip(),
        "round_off": request.form.get("round_off", "0").strip(),
        "grand_total": request.form.get("grand_total", "0").strip(),
        "terms": request.form.get("terms", "").strip(),
        "notes": request.form.get("notes", "").strip(),
        "status": "Generated",
        "client_email": current_user_email(),
        "created_by": current_user_email(),
        "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
    }


def post_invoice(invoice):
    user_email = invoice.get("client_email", current_user_email())
    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    ledger = load_json(LEDGER_FILE)
    ledger.append({
        "id": uuid.uuid4().hex,
        "type": "Invoice",
        "document_no": invoice.get("invoice_no"),
        "customer_name": invoice.get("customer_name"),
        "debit": invoice.get("grand_total", "0"),
        "credit": "0",
        "amount": invoice.get("grand_total", "0"),
        "status": "Receivable",
        "client_email": user_email,
        "created_at": now
    })
    save_json(LEDGER_FILE, ledger)

    gst_entries = load_json(GST_FILE)
    gst_entries.append({
        "id": uuid.uuid4().hex,
        "type": "Invoice",
        "document_no": invoice.get("invoice_no"),
        "customer_name": invoice.get("customer_name"),
        "gstin": invoice.get("customer_gst"),
        "taxable_amount": invoice.get("taxable_amount", "0"),
        "cgst": invoice.get("cgst", "0"),
        "sgst": invoice.get("sgst", "0"),
        "igst": invoice.get("igst", "0"),
        "total_gst": invoice.get("total_gst", "0"),
        "grand_total": invoice.get("grand_total", "0"),
        "client_email": user_email,
        "created_at": now
    })
    save_json(GST_FILE, gst_entries)

    tally = load_json(TALLY_FILE)
    tally.append({
        "id": uuid.uuid4().hex,
        "voucher_type": "Sales",
        "invoice_no": invoice.get("invoice_no"),
        "party_name": invoice.get("customer_name"),
        "amount": invoice.get("grand_total", "0"),
        "taxable_amount": invoice.get("taxable_amount", "0"),
        "gst_amount": invoice.get("total_gst", "0"),
        "client_email": user_email,
        "created_at": now
    })
    save_json(TALLY_FILE, tally)


def simple_doc_save(file_name, number_field, prefix, status):
    docs = load_json(file_name)
    number = request.form.get(number_field, "").strip() or generate_doc_no(prefix, docs)
    docs.insert(0, {
        "id": uuid.uuid4().hex,
        number_field: number,
        "customer_name": request.form.get("customer_name", "").strip(),
        "product_name": request.form.get("product_name", "").strip(),
        "hsn_code": request.form.get("hsn_code", "").strip(),
        "unit": request.form.get("unit", "").strip(),
        "qty": request.form.get("qty", "1").strip(),
        "rate": request.form.get("rate", "0").strip(),
        "gst_percent": request.form.get("gst_percent", "0").strip(),
        "grand_total": request.form.get("grand_total", "0").strip(),
        "status": status,
        "client_email": current_user_email(),
        "created_by": current_user_email(),
        "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
    })
    save_json(file_name, docs)


@documents_bp.route("/quotation", methods=["GET", "POST"])
@login_required
def quotation():
    quotations = load_json(QUOTATION_FILE)
    if request.method == "POST":
        simple_doc_save(QUOTATION_FILE, "quotation_no", "QT", "Pending")
        flash("Quotation saved successfully.", "success")
        return redirect(url_for("documents.quotation"))
    return render_template("documents/quotation.html", quotations=visible_data(quotations), customers=get_customer_names(), contracts=active_contracts(), doc_no=generate_doc_no("QT", quotations))


@documents_bp.route("/proforma", methods=["GET", "POST"])
@login_required
def proforma():
    proformas = load_json(PROFORMA_FILE)
    if request.method == "POST":
        simple_doc_save(PROFORMA_FILE, "proforma_no", "PI", "Pending")
        flash("Proforma invoice saved successfully.", "success")
        return redirect(url_for("documents.proforma"))
    return render_template("documents/proforma.html", proformas=visible_data(proformas), customers=get_customer_names(), contracts=active_contracts(), doc_no=generate_doc_no("PI", proformas))


@documents_bp.route("/invoice", methods=["GET", "POST"])
@login_required
def invoice():
    invoices = load_json(INVOICE_FILE)
    if request.method == "POST":
        invoice_no = request.form.get("invoice_no", "").strip() or generate_doc_no("INV", invoices)
        invoice_record = make_invoice_record(invoice_no)
        invoices.insert(0, invoice_record)
        save_json(INVOICE_FILE, invoices)
        post_invoice(invoice_record)
        flash("Invoice saved and posted to Ledger, GST and Tally/SAP successfully.", "success")
        return redirect(url_for("documents.invoice_register"))
    return render_template("documents/invoice.html", invoices=visible_data(invoices), customers=get_customer_names(), contracts=active_contracts(), doc_no=generate_doc_no("INV", invoices))


@documents_bp.route("/invoice-register")
@login_required
def invoice_register():
    invoices = visible_data(load_json(INVOICE_FILE))
    return render_template("documents/invoice_register.html", invoices=invoices)


@documents_bp.route("/invoice/preview/<invoice_id>")
@login_required
def invoice_preview(invoice_id):
    invoices = visible_data(load_json(INVOICE_FILE))
    invoice = next((i for i in invoices if i.get("id") == invoice_id), None)
    if not invoice:
        flash("Invoice not found.", "error")
        return redirect(url_for("documents.invoice_register"))
    return render_template("documents/invoice_preview.html", invoice=invoice)


@documents_bp.route("/delivery-challan", methods=["GET", "POST"])
@login_required
def delivery_challan():
    challans = load_json(DELIVERY_CHALLAN_FILE)
    if request.method == "POST":
        simple_doc_save(DELIVERY_CHALLAN_FILE, "challan_no", "DC", "Generated")
        flash("Delivery challan saved successfully.", "success")
        return redirect(url_for("documents.delivery_challan"))
    return render_template("documents/delivery_challan.html", challans=visible_data(challans), customers=get_customer_names(), contracts=active_contracts(), doc_no=generate_doc_no("DC", challans))


@documents_bp.route("/credit-note", methods=["GET", "POST"])
@login_required
def credit_note():
    invoices = visible_data(load_json(INVOICE_FILE))
    credit_notes = load_json(CREDIT_NOTE_FILE)
    if request.method == "POST":
        invoice_id = request.form.get("invoice_id", "")
        invoice = next((i for i in invoices if i.get("id") == invoice_id), None)
        if not invoice:
            flash("Please select valid invoice.", "error")
            return redirect(url_for("documents.credit_note"))
        cn_no = request.form.get("credit_note_no", "").strip() or generate_doc_no("CN", credit_notes)
        amount = request.form.get("amount", "").strip() or invoice.get("grand_total", "0")
        note = {
            "id": uuid.uuid4().hex,
            "credit_note_no": cn_no,
            "invoice_no": invoice.get("invoice_no"),
            "invoice_id": invoice.get("id"),
            "customer_name": invoice.get("customer_name"),
            "amount": amount,
            "reason": request.form.get("reason", "").strip(),
            "client_email": current_user_email(),
            "created_by": current_user_email(),
            "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        }
        credit_notes.insert(0, note)
        save_json(CREDIT_NOTE_FILE, credit_notes)

        ledger = load_json(LEDGER_FILE)
        ledger.append({"id": uuid.uuid4().hex, "type": "Credit Note", "document_no": cn_no, "customer_name": note.get("customer_name"), "debit": "0", "credit": amount, "amount": amount, "status": "Adjusted", "client_email": current_user_email(), "created_at": note["created_at"]})
        save_json(LEDGER_FILE, ledger)
        flash("Credit Note created successfully.", "success")
        return redirect(url_for("documents.credit_note"))
    return render_template("documents/credit_note.html", invoices=invoices, credit_notes=visible_data(credit_notes), doc_no=generate_doc_no("CN", credit_notes))


@documents_bp.route("/receipts")
@login_required
def receipts():
    return render_template("documents/receipts.html")
