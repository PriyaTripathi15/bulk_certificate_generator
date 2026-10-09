from pathlib import Path
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

OUTPUT_DIR = Path("generated_certificates")

def generate_certificate(name: str, course: str, certificate_id: str) -> str:
    """Generate one PDF using the single built-in certificate design."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{certificate_id}.pdf"
    page = landscape(A4)
    pdf = canvas.Canvas(str(path), pagesize=page)
    width, height = page
    pdf.setFillColor(colors.HexColor("#f8fbff"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#174a7e"))
    pdf.setLineWidth(5)
    pdf.rect(24, 24, width - 48, height - 48, fill=0, stroke=1)
    pdf.setStrokeColor(colors.HexColor("#d7ad45"))
    pdf.setLineWidth(1.5)
    pdf.rect(36, 36, width - 72, height - 72, fill=0, stroke=1)
    pdf.setFillColor(colors.HexColor("#174a7e"))
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(width / 2, height - 105, "CERTIFICATE OF COMPLETION")
    pdf.setFillColor(colors.HexColor("#333333"))
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(width / 2, height - 155, "This certificate is proudly presented to")
    pdf.setFillColor(colors.HexColor("#174a7e"))
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawCentredString(width / 2, height - 205, name)
    pdf.setFillColor(colors.HexColor("#333333"))
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(width / 2, height - 245, "for successfully completing")
    pdf.setFillColor(colors.HexColor("#222222"))
    pdf.setFont("Helvetica-Bold", 18)
    # Keep long course names within the page.
    course_text = course[:90] + ("..." if len(course) > 90 else "")
    pdf.drawCentredString(width / 2, height - 275, course_text)
    pdf.setStrokeColor(colors.HexColor("#777777"))
    pdf.line(width / 2 - 90, 100, width / 2 + 90, 100)
    pdf.setFillColor(colors.HexColor("#555555"))
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width / 2, 82, "Authorized Signature")
    pdf.drawString(55, 55, f"Certificate ID: {certificate_id}")
    pdf.save()
    return str(path)
