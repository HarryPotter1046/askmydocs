"""Generate the demo PDFs into docs/ — fake-but-realistic support docs with
specific, page-locatable facts so your citations resolve to a real page.

Requires reportlab:  pip install reportlab
Then:                python make_sample_pdfs.py
"""
import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

DOCS = {
    "refund_policy.pdf": [
        # page 1
        [
            ("Refund Policy", "Title"),
            ("Eligibility", "Heading2"),
            ("Refunds are accepted within 30 days of the delivery date. "
             "Orders placed more than 30 days ago are not eligible for a refund "
             "and will instead be offered store credit.", "BodyText"),
            ("Items must be unused and in their original packaging. Final-sale and "
             "personalized items cannot be refunded.", "BodyText"),
        ],
        # page 2
        [
            ("Refund Process & Timing", "Heading2"),
            ("Once we receive and inspect your return, refunds are issued to the "
             "original payment method within 5–7 business days.", "BodyText"),
            ("A 10% restocking fee applies to opened items. Original shipping "
             "charges are non-refundable.", "BodyText"),
        ],
    ],
    "shipping_policy.pdf": [
        # page 1
        [
            ("Shipping Policy", "Title"),
            ("Where We Ship", "Heading2"),
            ("We currently ship to 12 countries across North America and Europe. "
             "We do not ship to PO boxes or to Antarctica.", "BodyText"),
            ("Domestic orders arrive in 3–5 business days. International orders "
             "arrive in 7–14 business days.", "BodyText"),
        ],
        # page 2
        [
            ("Shipping Costs", "Heading2"),
            ("Standard domestic shipping is a flat $6. Orders over $75 ship free.",
             "BodyText"),
            ("Expedited 2-day shipping is available at checkout for $18.", "BodyText"),
        ],
    ],
    "warranty.pdf": [
        # page 1
        [
            ("Warranty", "Title"),
            ("Coverage", "Heading2"),
            ("All products carry a 1-year limited warranty covering defects in "
             "materials and workmanship from the date of purchase.", "BodyText"),
            ("The warranty does not cover accidental damage, normal wear, or "
             "damage from misuse.", "BodyText"),
        ],
        # page 2
        [
            ("Making a Claim", "Heading2"),
            ("To file a claim, email support@example.com with your order number "
             "and a photo of the defect. Approved claims are repaired or replaced "
             "free of charge.", "BodyText"),
        ],
    ],
}


def build(filename, pages):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(os.path.join("docs", filename), pagesize=letter)
    flow = []
    for i, blocks in enumerate(pages):
        if i > 0:
            flow.append(PageBreak())
        for text, style in blocks:
            flow.append(Paragraph(text, styles[style]))
            flow.append(Spacer(1, 12))
    doc.build(flow)
    print(f"Wrote docs/{filename} ({len(pages)} pages)")


if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    for filename, pages in DOCS.items():
        build(filename, pages)
    print("\nDone. Next: python ingest.py")
