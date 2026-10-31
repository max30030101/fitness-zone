from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_invoice_pdf(order):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Invoice for order {order.pk}",
        author=settings.SITE_NAME,
    )
    styles = getSampleStyleSheet()
    normal = styles["BodyText"]
    address = "<br/>".join(
        escape(part)
        for part in (
            order.full_name,
            order.address_line,
            order.city,
            f"{order.state} {order.pincode}",
            f"Phone: {order.phone}",
        )
    )
    story = [
        Paragraph(escape(settings.SITE_NAME), styles["Title"]),
        Paragraph("ORDER INVOICE", styles["Heading2"]),
        Spacer(1, 5 * mm),
        Paragraph(f"<b>Invoice / Order #:</b> {order.pk}", normal),
        Paragraph(
            f"<b>Order date:</b> {timezone.localtime(order.created_at).strftime('%d %b %Y')}",
            normal,
        ),
        Paragraph(f"<b>Status:</b> {escape(order.get_status_display())}", normal),
        Spacer(1, 5 * mm),
        Paragraph("<b>Bill to</b>", normal),
        Paragraph(address, normal),
        Spacer(1, 8 * mm),
    ]

    rows = [["Item", "Qty", "Unit price (INR)", "Amount (INR)"]]
    for item in order.items.all():
        rows.append([
            Paragraph(escape(item.product_name), normal),
            str(item.quantity),
            f"{item.unit_price:,.2f}",
            f"{item.line_total:,.2f}",
        ])
    rows.extend([
        ["", "", "Subtotal", f"{order.subtotal:,.2f}"],
        ["", "", "Shipping", f"{order.shipping:,.2f}"],
        ["", "", "Total", f"{order.total:,.2f}"],
    ])
    table = Table(rows, colWidths=[82 * mm, 14 * mm, 39 * mm, 39 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#151b17")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, -3), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -4), 0.4, colors.HexColor("#cbd2cc")),
        ("LINEABOVE", (2, -3), (-1, -3), 0.7, colors.HexColor("#87918a")),
        ("LINEABOVE", (2, -1), (-1, -1), 1, colors.HexColor("#151b17")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([
        table,
        Spacer(1, 8 * mm),
        Paragraph(f"Payment method: {escape(order.get_payment_method_display())}", normal),
        Paragraph(f"Thank you for shopping with {escape(settings.SITE_NAME)}.", normal),
    ])
    document.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="order-{order.pk}-invoice.pdf"'
    return response
