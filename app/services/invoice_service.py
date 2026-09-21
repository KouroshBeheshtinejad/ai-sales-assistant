from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def render_invoice_pdf(order) -> bytes:
    output = BytesIO()
    document = canvas.Canvas(output, pagesize=A4)
    _, height = A4
    y = height - 56
    document.setTitle(order.invoice_number)
    document.setFont("Helvetica-Bold", 16)
    document.drawString(48, y, "NAVA INVOICE")
    y -= 28
    document.setFont("Helvetica", 10)
    for label, value in (("Invoice", order.invoice_number), ("Tracking", order.tracking_number), ("Store", order.store.name), ("Customer", order.customer_name), ("Email", order.customer_email or "-"), ("Phone", order.customer_phone), ("Address", order.customer_address), ("Status", order.status)):
        document.drawString(48, y, f"{label}: {value}")
        y -= 16
    y -= 10
    document.setFont("Helvetica-Bold", 10)
    document.drawString(48, y, "Item")
    document.drawString(300, y, "Qty")
    document.drawString(350, y, "Unit price")
    document.drawString(450, y, "Line total")
    y -= 16
    document.setFont("Helvetica", 10)
    for item in order.items:
        document.drawString(48, y, item.product_name[:38])
        document.drawRightString(330, y, str(item.quantity))
        document.drawRightString(430, y, str(item.unit_price))
        document.drawRightString(530, y, str(item.line_total))
        y -= 16
        if y < 72:
            document.showPage()
            y = height - 56
    document.setFont("Helvetica-Bold", 11)
    document.drawRightString(530, y - 12, f"Total: {order.total_amount}")
    document.save()
    return output.getvalue()