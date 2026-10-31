"""Generates the demo documents (text-layer PDFs + one PNG) and their ground-truth labels.

    python -m app.utils.sample_docs        # writes ../samples/*
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.core.config import BACKEND_DIR

SAMPLES_DIR = BACKEND_DIR.parent / "samples"

SAMPLES = [
    {
        "file": "A_invoice_pune_techsupplies.pdf",
        "scenario": "A - Successful processing",
        "title": "TAX INVOICE",
        "org": "Pune TechSupplies Pvt. Ltd.",
        "lines": [
            "Invoice No: INV-2026-0918",
            "Invoice Date: 18/10/2026",
            "Due Date: 17/11/2026",
            "Vendor: Pune TechSupplies Pvt. Ltd.",
            "GSTIN: 27AABCP1234Q1Z5",
            "Bill To: Nutan Maharashtra Institute of Engineering and Technology",
            "PO Number: PO-NMIET-2026-311",
            "",
            "Items: 12 x Wireless keyboard-mouse set, 4 x 24-inch monitor, cabling",
            "Subtotal: 41,152.54",
            "GST @18%: 7,407.46",
            "Total Amount: INR 48,560.00",
            "Currency: INR",
        ],
        "truth": {"invoice_number": "INV-2026-0918", "vendor_name": "Pune TechSupplies Pvt. Ltd.",
                  "vendor_gstin": "27AABCP1234Q1Z5", "invoice_date": "2026-10-18", "due_date": "2026-11-17",
                  "total_amount": "48560.00", "currency": "INR", "po_number": "PO-NMIET-2026-311"},
    },
    {
        "file": "B_admission_form_missing_field.pdf",
        "scenario": "B - Missing information",
        "title": "ADMISSION FORM 2026-27",
        "org": "NMIET Admissions Office",
        "lines": [
            "Applicant Name: Riya Sanjay Kulkarni",
            "Date of Birth: 14/03/2008",
            "Email: riya.kulkarni08@example.com",
            "Phone: +91 98220 41753",
            "Course Applied: B.E. Computer Engineering",
            "HSC Percentage: 86.40",
            "Category: Open",
            "Guardian Name:",
            "Address: Flat 7, Shivneri Apartments, Talegaon Dabhade, Pune 410507",
            "",
            "Declaration: I confirm the above information is correct.",
        ],
        "truth": {"applicant_name": "Riya Sanjay Kulkarni", "date_of_birth": "2008-03-14",
                  "email": "riya.kulkarni08@example.com", "course_applied": "B.E. Computer Engineering",
                  "previous_marks_percent": "86.40", "guardian_name": None},
    },
    {
        "file": "C_invoice_duplicate.pdf",
        "scenario": "C - Duplicate detection",
        "title": "TAX INVOICE",
        "org": "Shree Ganesh Office Supplies",
        "lines": [
            "Invoice No: INV-SGO-2026-0412",
            "Invoice Date: 02/09/2026",
            "Due Date: 02/10/2026",
            "Vendor: Shree Ganesh Office Supplies",
            "GSTIN: 27AAKFS5521M1Z2",
            "Bill To: Nutan Maharashtra Institute of Engineering and Technology",
            "",
            "Items: 40 reams A4 paper, 25 whiteboard markers, 10 box files",
            "Total Amount: INR 18,240.00",
            "Currency: INR",
        ],
        "truth": {"invoice_number": "INV-SGO-2026-0412", "vendor_name": "Shree Ganesh Office Supplies",
                  "vendor_gstin": "27AAKFS5521M1Z2", "invoice_date": "2026-09-02", "total_amount": "18240.00"},
    },
    {
        "file": "D_fee_receipt_unclear_amount.pdf",
        "scenario": "D - Low confidence",
        "title": "FEE RECEIPT",
        "org": "NMIET Accounts Section",
        "lines": [
            "Receipt No: FR-2026-11873",
            "Student Name: Omkar Deshmukh",
            "Student ID: NMIET-CE-2024-118",
            "Course: B.E. Computer Engineering (Second Year)",
            "Academic Year: 2026-27",
            "Amount Paid: Rs. 4?,500.00",
            "Payment Date: 1?/10/2026",
            "Payment Mode: UPI",
            "",
            "(Scanned copy - ink smudged near amount and date)",
        ],
        "truth": {"receipt_number": "FR-2026-11873", "student_name": "Omkar Deshmukh",
                  "student_id": "NMIET-CE-2024-118", "amount_paid": None, "payment_date": None, "payment_mode": "UPI"},
    },
    {
        "file": "E_complaint_email_hostel_leak.pdf",
        "scenario": "E - Complaint processing",
        "title": "EMAIL - COMPLAINT",
        "org": "registrar@nmiet.example.edu inbox",
        "lines": [
            "From: aarav.patil.cs22@example.com",
            "Name: Aarav Patil",
            "Date: 29/10/2026",
            "Subject: Water leakage and exposed wiring in Hostel Block C",
            "Location: Hostel Block C, 2nd floor corridor",
            "",
            "Respected Sir/Madam,",
            "There is continuous water leakage from the ceiling near room C-214 since three days.",
            "The water is dripping next to an electric switch board and two students got a mild shock.",
            "This is unsafe. Please send the maintenance team urgently.",
            "Regards, Aarav Patil (TE Computer)",
        ],
        "truth": {"sender_email": "aarav.patil.cs22@example.com", "sender_name": "Aarav Patil",
                  "subject": "Water leakage and exposed wiring in Hostel Block C", "received_date": "2026-10-29",
                  "complaint_category": "Facilities & Maintenance", "urgency": "high"},
    },
    {
        "file": "F_clinic_registration.pdf",
        "scenario": "Extra - Clinic registration",
        "title": "PATIENT REGISTRATION",
        "org": "Sahyadri Family Clinic, Talegaon",
        "lines": [
            "Patient Name: Meera Joshi",
            "Date of Birth: 22/07/1991",
            "Gender: Female",
            "Phone: +91 99702 18834",
            "Emergency Contact: Nikhil Joshi (+91 98500 66120)",
            "Insurance ID: STAR-HLT-883421",
            "Reason for Visit: Persistent cough and mild fever for 5 days",
            "Preferred Doctor: Dr. A. Bhosale",
        ],
        "truth": {"patient_name": "Meera Joshi", "date_of_birth": "1991-07-22", "phone": "+91 99702 18834",
                  "insurance_id": "STAR-HLT-883421", "preferred_doctor": "Dr. A. Bhosale"},
    },
]


def _pdf(path: Path, sample: dict) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    c.setFillColor(HexColor("#101828"))
    c.rect(0, h - 70, w, 70, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, h - 42, sample["title"])
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 40, h - 42, sample["org"])
    c.setFillColor(HexColor("#101828"))
    y = h - 110
    for line in sample["lines"]:
        c.setFont("Helvetica", 11)
        c.drawString(48, y, line)
        y -= 22
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(HexColor("#98A2B3"))
    c.drawString(40, 30, "ActionLoop demo document - fictitious data for demonstration only")
    c.save()


def _png(path: Path) -> None:
    img = Image.new("RGB", (900, 620), "#F7F8FA")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
        small = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = small = ImageFont.load_default()
    d.rectangle([0, 0, 900, 70], fill="#101828")
    d.text((30, 22), "TAX INVOICE  (photographed copy)", fill="white", font=font)
    rows = ["Invoice No: INV-2026-1021", "Invoice Date: 21/10/2026", "Vendor: Deccan Lab Instruments",
            "GSTIN: 27AADCD7781K1Z9", "Total Amount: INR 1,12,400.00"]
    for i, r in enumerate(rows):
        d.text((40, 110 + i * 48), r, fill="#101828", font=font)
    d.text((40, 570), "ActionLoop demo document - fictitious data", fill="#98A2B3", font=small)
    img.save(path)


def generate(out_dir: Path = SAMPLES_DIR) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for s in SAMPLES:
        _pdf(out_dir / s["file"], s)
        manifest.append({"file": s["file"], "scenario": s["scenario"], "truth": s["truth"]})
    _png(out_dir / "G_invoice_photo.png")
    manifest.append({"file": "G_invoice_photo.png", "scenario": "Image upload (needs vision LLM)", "truth": {}})
    (out_dir / "ground_truth.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    for m in generate():
        print(m["file"], "-", m["scenario"])
