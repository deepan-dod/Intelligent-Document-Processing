"""Generates the five-document example scenario (PO/Delivery/Invoice/Contract/Certificate) as real PDFs."""
import os, tempfile
import fitz

def make_pdf(path, lines, producer=None):
    doc = fitz.open(); page = doc.new_page()
    y = 60
    for i, t in enumerate(lines):
        page.insert_text((60, y), t, fontsize=18 if i == 0 else 12); y += 28
    if producer: doc.set_metadata({"producer": producer})
    doc.save(path); doc.close()

SCENARIO = {
 "contract.pdf": ["CONTRACT AGREEMENT", "Contract ID: CON-71", "Parties: ABC Technologies Pvt Ltd and Zenith Supplies Pvt Ltd", "Start Date: 01-01-2026",
                  "End Date: 31-12-2027", "Contract Value: 500000", "Terms: Supply of components", "Obligations: Deliver goods per purchase orders"],
 "purchase_order.pdf": ["PURCHASE ORDER", "PO Number: PO-1023", "Organization: ABC Technologies Pvt Ltd", "Supplier: Zenith Supplies Pvt Ltd", "Order Date: 05-09-2026",
                        "Items: Sensors", "Quantity: 10", "Unit Price: 1500", "Delivery Date: 30-09-2026", "Contract Ref: CON-71"],
 "delivery.pdf": ["DELIVERY NOTE", "Delivery Note No: DEL-55", "PO Number: PO-1023", "Supplier: Zenith Supplies Pvt Ltd", "Consignee: ABC Technologies",
                  "Delivery Date: 30-09-2026", "Items: Sensors", "Quantity Delivered: 10"],
 "invoice.pdf": ["INVOICE", "Invoice Number: INV-889", "Vendor: Zenith Supplies Pvt Ltd", "Bill To: A.B.C Technologies", "Invoice Date: 02-10-2026",
                 "Items: Sensors", "Quantity: 12", "Unit Price: 1500", "Tax: 3240", "Total: 21240", "PO Reference: PO-1023"],
 "certificate.pdf": ["CERTIFICATE OF COMPLIANCE", "Certificate ID: CERT-19", "Holder: Zenith Supplies Pvt Ltd", "Issuing Organization: Quality Council Ltd",
                     "Issue Date: 08-10-2025", "Expiry Date: 30-05-2027", "Certificate Type: ISO Compliance", "Contract Ref: CON-71"],
}

def load_demo():
    import pipeline
    from documents.upload import save_upload
    from database.models import db, Document
    from werkzeug.datastructures import FileStorage
    tmp = tempfile.mkdtemp(); ids = []
    for name, lines in SCENARIO.items():
        p = os.path.join(tmp, name); make_pdf(p, lines)
        with open(p, "rb") as fh:
            d = save_upload(FileStorage(fh, filename=name), "demo"); pipeline.process_document(d.id); ids.append(d.id)
    return f"Loaded documents {ids}"
