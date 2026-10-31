"""Supported document types: classification keywords and field specifications.

Each field spec has the label printed on real documents (used by the deterministic DEMO-mode
parser) plus a value pattern. The same specs drive the LLM JSON schema and the UI.
"""

DATE = r"(\d{1,2}[/\-.][0-9?]{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2} [A-Z][a-z]{2,8} \d{4})"
AMOUNT = r"((?:INR|Rs\.?|₹)?\s*[0-9?][0-9?,]*(?:\.[0-9?]{2})?)"
TEXT = r"(.+)"

DOCUMENT_TYPES: dict[str, dict] = {
    "invoice": {
        "label": "Business Invoice",
        "keywords": ["tax invoice", "invoice no", "gstin", "bill to", "due date", "invoice"],
        "fields": [
            {"name": "invoice_number", "label": "Invoice Number", "aliases": ["Invoice No", "Invoice Number", "Invoice #"], "pattern": r"([A-Z0-9][A-Z0-9\-/]{3,})", "required": True},
            {"name": "vendor_name", "label": "Vendor", "aliases": ["Vendor", "From", "Seller"], "pattern": TEXT, "required": True},
            {"name": "vendor_gstin", "label": "Vendor GSTIN", "aliases": ["GSTIN", "Vendor GSTIN"], "pattern": r"([0-9A-Z?]{15})", "required": True},
            {"name": "buyer_name", "label": "Bill To", "aliases": ["Bill To", "Buyer"], "pattern": TEXT, "required": False},
            {"name": "po_number", "label": "PO Number", "aliases": ["PO Number", "PO No", "Purchase Order"], "pattern": r"([A-Z0-9\-/]+)", "required": False},
            {"name": "invoice_date", "label": "Invoice Date", "aliases": ["Invoice Date", "Date"], "pattern": DATE, "required": True},
            {"name": "due_date", "label": "Due Date", "aliases": ["Due Date"], "pattern": DATE, "required": False},
            {"name": "total_amount", "label": "Total Amount", "aliases": ["Total Amount", "Grand Total", "Amount Due", "Total"], "pattern": AMOUNT, "required": True},
            {"name": "currency", "label": "Currency", "aliases": ["Currency"], "pattern": r"([A-Z]{3})", "required": False},
        ],
    },
    "fee_receipt": {
        "label": "Student Fee Receipt",
        "keywords": ["fee receipt", "receipt no", "student id", "academic year", "amount paid", "tuition"],
        "fields": [
            {"name": "receipt_number", "label": "Receipt Number", "aliases": ["Receipt No", "Receipt Number"], "pattern": r"([A-Z0-9][A-Z0-9\-/]{3,})", "required": True},
            {"name": "student_name", "label": "Student Name", "aliases": ["Student Name", "Name"], "pattern": TEXT, "required": True},
            {"name": "student_id", "label": "Student ID", "aliases": ["Student ID", "PRN", "Roll No"], "pattern": r"([A-Z0-9\-]{4,})", "required": True},
            {"name": "course", "label": "Course", "aliases": ["Course", "Programme", "Program"], "pattern": TEXT, "required": True},
            {"name": "academic_year", "label": "Academic Year", "aliases": ["Academic Year"], "pattern": r"(\d{4}\s*-\s*\d{2,4})", "required": False},
            {"name": "amount_paid", "label": "Amount Paid", "aliases": ["Amount Paid", "Total Paid", "Amount"], "pattern": AMOUNT, "required": True},
            {"name": "payment_date", "label": "Payment Date", "aliases": ["Payment Date", "Date"], "pattern": DATE, "required": True},
            {"name": "payment_mode", "label": "Payment Mode", "aliases": ["Payment Mode", "Mode"], "pattern": TEXT, "required": False},
        ],
    },
    "admission_form": {
        "label": "College Admission Form",
        "keywords": ["admission form", "applicant", "course applied", "guardian", "date of birth", "admission"],
        "fields": [
            {"name": "applicant_name", "label": "Applicant Name", "aliases": ["Applicant Name", "Full Name"], "pattern": TEXT, "required": True},
            {"name": "date_of_birth", "label": "Date of Birth", "aliases": ["Date of Birth", "DOB"], "pattern": DATE, "required": True},
            {"name": "email", "label": "Email", "aliases": ["Email", "E-mail"], "pattern": r"([\w.+\-]+@[\w\-]+\.[\w.\-]+)", "required": True},
            {"name": "phone", "label": "Phone", "aliases": ["Phone", "Mobile"], "pattern": r"(\+?[0-9][0-9 \-]{8,14})", "required": True},
            {"name": "course_applied", "label": "Course Applied", "aliases": ["Course Applied", "Course"], "pattern": TEXT, "required": True},
            {"name": "previous_marks_percent", "label": "HSC Percentage", "aliases": ["HSC Percentage", "Previous Marks", "12th Percentage"], "pattern": r"([0-9]{1,3}(?:\.[0-9]{1,2})?)\s*%?", "required": True},
            {"name": "category", "label": "Category", "aliases": ["Category"], "pattern": TEXT, "required": False},
            {"name": "guardian_name", "label": "Guardian Name", "aliases": ["Guardian Name", "Parent Name"], "pattern": TEXT, "required": True},
            {"name": "address", "label": "Address", "aliases": ["Address"], "pattern": TEXT, "required": False},
        ],
    },
    "clinic_registration": {
        "label": "Clinic Registration Form",
        "keywords": ["patient registration", "patient name", "clinic", "emergency contact", "symptoms", "doctor"],
        "fields": [
            {"name": "patient_name", "label": "Patient Name", "aliases": ["Patient Name"], "pattern": TEXT, "required": True},
            {"name": "date_of_birth", "label": "Date of Birth", "aliases": ["Date of Birth", "DOB"], "pattern": DATE, "required": True},
            {"name": "gender", "label": "Gender", "aliases": ["Gender", "Sex"], "pattern": TEXT, "required": False},
            {"name": "phone", "label": "Phone", "aliases": ["Phone", "Mobile"], "pattern": r"(\+?[0-9][0-9 \-]{8,14})", "required": True},
            {"name": "emergency_contact", "label": "Emergency Contact", "aliases": ["Emergency Contact"], "pattern": TEXT, "required": True},
            {"name": "insurance_id", "label": "Insurance ID", "aliases": ["Insurance ID", "Policy No"], "pattern": r"([A-Z0-9\-]{5,})", "required": False},
            {"name": "visit_reason", "label": "Reason for Visit", "aliases": ["Reason for Visit", "Symptoms"], "pattern": TEXT, "required": True},
            {"name": "preferred_doctor", "label": "Preferred Doctor", "aliases": ["Preferred Doctor", "Doctor"], "pattern": TEXT, "required": False},
        ],
    },
    "complaint_email": {
        "label": "Administrative Complaint",
        "keywords": ["complaint", "subject:", "from:", "issue", "grievance", "not working", "urgent"],
        "fields": [
            {"name": "sender_name", "label": "Sender Name", "aliases": ["Name", "Sender"], "pattern": TEXT, "required": True},
            {"name": "sender_email", "label": "Sender Email", "aliases": ["From", "Email"], "pattern": r"([\w.+\-]+@[\w\-]+\.[\w.\-]+)", "required": True},
            {"name": "subject", "label": "Subject", "aliases": ["Subject"], "pattern": TEXT, "required": True},
            {"name": "received_date", "label": "Date", "aliases": ["Date", "Sent"], "pattern": DATE, "required": True},
            {"name": "location", "label": "Location", "aliases": ["Location", "Room", "Block"], "pattern": TEXT, "required": False},
            {"name": "description", "label": "Complaint Summary", "aliases": [], "pattern": TEXT, "required": True},
            {"name": "complaint_category", "label": "Category (derived)", "aliases": [], "pattern": TEXT, "required": False},
            {"name": "urgency", "label": "Urgency (derived)", "aliases": [], "pattern": TEXT, "required": False},
        ],
    },
}

COMPLAINT_CATEGORIES = {
    "Facilities & Maintenance": ["water", "leak", "electric", "power", "fan", "light", "ac ", "air condition", "washroom", "repair", "broken", "lift"],
    "IT Services": ["wifi", "wi-fi", "internet", "network", "login", "portal", "computer", "lab pc", "email account"],
    "Accounts & Fees": ["fee", "refund", "payment", "receipt", "scholarship"],
    "Academics": ["exam", "result", "marks", "attendance", "lecture", "faculty", "timetable"],
    "Safety & Security": ["safety", "fire", "harass", "security", "theft", "injury", "unsafe"],
}

CATEGORY_DEPARTMENT = {
    "Facilities & Maintenance": "Estate & Maintenance Office",
    "IT Services": "IT Helpdesk",
    "Accounts & Fees": "Accounts Department",
    "Academics": "Academic Office",
    "Safety & Security": "Security & Safety Cell",
    "General Administration": "Registrar's Office",
}

URGENT_WORDS = ["urgent", "immediately", "asap", "danger", "unsafe", "fire", "injury", "since 3 days", "since three days", "emergency", "shock"]


def field_specs(doc_type: str) -> list[dict]:
    return DOCUMENT_TYPES.get(doc_type, {}).get("fields", [])


def type_label(doc_type: str | None) -> str:
    return DOCUMENT_TYPES.get(doc_type or "", {}).get("label", "Unknown Document")
