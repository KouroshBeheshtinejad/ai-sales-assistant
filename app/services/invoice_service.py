"""Renders the PDF invoice attached to an order.

The store name, customer name and delivery address are almost always Persian, so this
module embeds a Persian-capable font (Vazirmatn, bundled under ``app/assets/fonts``)
instead of relying on reportlab's built-in Helvetica, which only covers Latin-1 and
silently draws unsupported glyphs as black "tofu" squares.

Reportlab also does not perform Arabic/Persian text shaping or bidi reordering on its
own: it draws whatever codepoints it is given, left to right, glyph by glyph. Persian
letters change shape depending on their neighbours (isolated / initial / medial /
final forms), so every piece of Persian text is run through ``arabic_reshaper`` to pick
the correct presentation-form glyphs and then through ``python-bidi`` to lay them out
in the correct visual (right-to-left) order before it reaches reportlab.
"""

from __future__ import annotations

from datetime import timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import arabic_reshaper
import jdatetime
from babel.dates import format_datetime
from babel.numbers import format_decimal
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_REGULAR = "Vazirmatn"
FONT_MEDIUM = "Vazirmatn-Medium"
FONT_BOLD = "Vazirmatn-Bold"

TEAL_INK = colors.HexColor("#0b5f5a")
TEAL_SOFT = colors.HexColor("#e3f3f1")
MUTED = colors.HexColor("#5b7278")
LINE = colors.HexColor("#d8e4e3")
INK = colors.HexColor("#132b30")

STATUS_LABELS_FA = {
    "pending": "در انتظار",
    "confirmed": "تأیید شد",
    "preparing": "در حال آماده‌سازی",
    "shipped": "ارسال شد",
    "delivered": "تحویل شد",
    "cancelled": "لغو شد",
}
STATUS_LABELS = {
    "fa": STATUS_LABELS_FA,
    "en": {"pending": "Pending", "confirmed": "Confirmed", "preparing": "Preparing", "shipped": "Shipped", "delivered": "Delivered", "cancelled": "Cancelled"},
    "es": {"pending": "Pendiente", "confirmed": "Confirmado", "preparing": "En preparación", "shipped": "Enviado", "delivered": "Entregado", "cancelled": "Cancelado"},
    "de": {"pending": "Ausstehend", "confirmed": "Bestätigt", "preparing": "In Vorbereitung", "shipped": "Versendet", "delivered": "Zugestellt", "cancelled": "Storniert"},
    "fr": {"pending": "En attente", "confirmed": "Confirmée", "preparing": "En préparation", "shipped": "Expédiée", "delivered": "Livrée", "cancelled": "Annulée"},
}

SUPPORTED_LOCALES = {"fa", "en", "es", "de", "fr"}
INVOICE_TEXT = {
    "fa": {"title": "فاکتور فروش", "invoice": "شماره فاکتور", "order": "شماره سفارش", "tracking": "کد رهگیری", "issued": "تاریخ صدور", "timezone": "منطقه زمانی", "status": "وضعیت سفارش", "payment": "وضعیت پرداخت", "paid": "پرداخت‌شده", "seller": "فروشنده", "customer": "مشخصات مشتری", "items": "اقلام سفارش", "row": "ردیف", "product": "کالا", "quantity": "تعداد", "unit": "قیمت واحد", "sum": "جمع", "subtotal": "جمع جزء", "total": "جمع کل", "email": "ایمیل", "phone": "تلفن", "address": "آدرس", "footer": "این فاکتور توسط ناوا صادر شده است — دستیار فروش هوشمند فروشگاه‌های آنلاین", "currency": "تومان"},
    "en": {"title": "Sales Invoice", "invoice": "Invoice number", "order": "Order number", "tracking": "Tracking number", "issued": "Issued", "timezone": "Time zone", "status": "Order status", "payment": "Payment status", "paid": "Paid", "seller": "Seller", "customer": "Customer details", "items": "Order items", "row": "No.", "product": "Product", "quantity": "Qty", "unit": "Unit price", "sum": "Amount", "subtotal": "Subtotal", "total": "Total", "email": "Email", "phone": "Phone", "address": "Address", "footer": "Issued by NAVA, the intelligent sales assistant for online stores", "currency": "Toman"},
    "es": {"title": "Factura de venta", "invoice": "Número de factura", "order": "Número de pedido", "tracking": "Número de seguimiento", "issued": "Fecha de emisión", "timezone": "Zona horaria", "status": "Estado del pedido", "payment": "Estado del pago", "paid": "Pagado", "seller": "Vendedor", "customer": "Datos del cliente", "items": "Artículos del pedido", "row": "N.º", "product": "Producto", "quantity": "Cant.", "unit": "Precio unitario", "sum": "Importe", "subtotal": "Subtotal", "total": "Total", "email": "Correo", "phone": "Teléfono", "address": "Dirección", "footer": "Emitida por NAVA, el asistente inteligente de ventas para tiendas online", "currency": "tomanes"},
    "de": {"title": "Verkaufsrechnung", "invoice": "Rechnungsnummer", "order": "Bestellnummer", "tracking": "Sendungsnummer", "issued": "Ausgestellt am", "timezone": "Zeitzone", "status": "Bestellstatus", "payment": "Zahlungsstatus", "paid": "Bezahlt", "seller": "Verkäufer", "customer": "Kundendaten", "items": "Bestellpositionen", "row": "Nr.", "product": "Produkt", "quantity": "Anz.", "unit": "Einzelpreis", "sum": "Betrag", "subtotal": "Zwischensumme", "total": "Gesamtbetrag", "email": "E-Mail", "phone": "Telefon", "address": "Adresse", "footer": "Ausgestellt von NAVA, dem intelligenten Verkaufsassistenten für Online-Shops", "currency": "Toman"},
    "fr": {"title": "Facture de vente", "invoice": "Numéro de facture", "order": "Numéro de commande", "tracking": "Numéro de suivi", "issued": "Date d’émission", "timezone": "Fuseau horaire", "status": "État de la commande", "payment": "État du paiement", "paid": "Payé", "seller": "Vendeur", "customer": "Coordonnées du client", "items": "Articles commandés", "row": "N°", "product": "Produit", "quantity": "Qté", "unit": "Prix unitaire", "sum": "Montant", "subtotal": "Sous-total", "total": "Total", "email": "E-mail", "phone": "Téléphone", "address": "Adresse", "footer": "Émise par NAVA, l’assistant commercial intelligent pour les boutiques en ligne", "currency": "tomans"},
}


LOCALE_TAGS = {"fa": "fa_IR", "en": "en_US", "es": "es_ES", "de": "de_DE", "fr": "fr_FR"}


def _register_fonts() -> None:
    # Runs once per interpreter: importing this module a second time is a no-op in
    # CPython, but a dev auto-reloader can re-exec it, so registration is defensive.
    try:
        pdfmetrics.getFont(FONT_REGULAR)
        return
    except KeyError:
        pass
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(FONT_DIR / "Vazirmatn-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_MEDIUM, str(FONT_DIR / "Vazirmatn-Medium.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_DIR / "Vazirmatn-Bold.ttf")))
    pdfmetrics.registerFontFamily(FONT_REGULAR, normal=FONT_REGULAR, bold=FONT_BOLD)


_register_fonts()


def rtl(value) -> str:
    """Shapes and bidi-reorders text so reportlab renders Persian/Arabic correctly.

    Safe to call on any string, including plain Latin/digits: arabic_reshaper leaves
    non-Arabic characters untouched and get_display's bidi reordering is a no-op when
    there is nothing right-to-left to reorder.
    """
    text = "" if value is None else str(value)
    if not text.strip():
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def money(value, locale="fa") -> str:
    """Formats an amount as plain (unshaped) text — callers route it through ``_p()``,
    which shapes it exactly once. Shaping this twice un-reverses the bidi reordering
    and renders as garbled/reversed Persian, so this must NOT call ``rtl()`` itself.
    """
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError):
        return f"{value} {INVOICE_TEXT[locale]['currency']}"
    amount = amount.quantize(Decimal("1")) if amount == amount.to_integral_value() else amount.quantize(Decimal("0.01"))
    if locale == "fa":
        return f"{amount:,} تومان"
    return f"{format_decimal(amount, locale=LOCALE_TAGS[locale])} {INVOICE_TEXT[locale]['currency']}"


def _style(name, font=FONT_REGULAR, size=10, leading=None, align=TA_RIGHT, color=INK, **extra):
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading or size * 1.5, alignment=align, textColor=color, **extra)


STYLES = {
    "brand": _style("brand", font=FONT_BOLD, size=18, align=TA_LEFT, color=TEAL_INK),
    "doc_title": _style("doc_title", font=FONT_BOLD, size=15, align=TA_RIGHT),
    "meta_label": _style("meta_label", font=FONT_MEDIUM, size=9, align=TA_RIGHT, color=MUTED),
    "meta_value": _style("meta_value", font=FONT_BOLD, size=10, align=TA_RIGHT),
    "section": _style("section", font=FONT_BOLD, size=11, align=TA_RIGHT, color=TEAL_INK, spaceAfter=4 * mm),
    "body": _style("body", font=FONT_REGULAR, size=10, align=TA_RIGHT),
    "body_muted": _style("body_muted", font=FONT_REGULAR, size=9.5, align=TA_RIGHT, color=MUTED),
    "th": _style("th", font=FONT_BOLD, size=9.5, align=TA_CENTER, color=colors.white),
    "td": _style("td", font=FONT_REGULAR, size=9.5, align=TA_CENTER),
    "td_name": _style("td_name", font=FONT_REGULAR, size=9.5, align=TA_RIGHT),
    "total_label": _style("total_label", font=FONT_BOLD, size=11, align=TA_RIGHT),
    "total_value": _style("total_value", font=FONT_BOLD, size=13, align=TA_RIGHT, color=TEAL_INK),
    "footer": _style("footer", font=FONT_REGULAR, size=8.5, align=TA_CENTER, color=MUTED),
}


def _p(text, style, locale="fa"):
    paragraph_style = STYLES[style]
    if locale != "fa" and paragraph_style.alignment == TA_RIGHT:
        paragraph_style = ParagraphStyle(f"{style}_ltr", parent=paragraph_style, alignment=TA_LEFT)
    return Paragraph(rtl(text) if locale == "fa" else str(text), paragraph_style)


def _meta_row(pairs, width, locale="fa"):
    """A compact label/value list that remains readable as metadata fields grow."""
    rows = []
    for label, value in pairs:
        values = [_p(value, "meta_value", locale), _p(label, "meta_label", locale)]
        rows.append(values if locale == "fa" else list(reversed(values)))
    table = Table(
        rows,
        colWidths=[width * 0.62, width * 0.38],
        hAlign="RIGHT" if locale == "fa" else "LEFT",
    )
    table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _items_table(items, width, locale="fa", header_labels=None):
    # Physical column order is left-to-right; the *last* column ends up on the right
    # edge of the page, which is where a right-to-left reader expects the row number.
    labels = INVOICE_TEXT[locale]
    header_labels = header_labels or [labels[key] for key in (("sum", "unit", "quantity", "product", "row") if locale == "fa" else ("row", "product", "quantity", "unit", "sum"))]
    header = [_p(label, "th", locale) for label in header_labels]
    rows = [header]
    for index, item in enumerate(items, start=1):
        values = [
            _p(money(item.line_total, locale), "td", locale),
            _p(money(item.unit_price, locale), "td", locale),
            _p(item.quantity, "td", locale),
            _p(item.product_name, "td_name", locale),
            _p(index, "td", locale),
        ]
        rows.append(values if locale == "fa" else list(reversed(values)))
    col_widths = [width * part for part in ((0.20, 0.20, 0.12, 0.36, 0.12) if locale == "fa" else (0.12, 0.36, 0.12, 0.20, 0.20))]
    table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="RIGHT" if locale == "fa" else "LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL_INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TEAL_SOFT]),
        ("GRID", (0, 0), (-1, -1), 0.6, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _effective_timezone(locale: str, timezone_name: str) -> str:
    if locale == "fa":
        return "Asia/Tehran"
    try:
        ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        return "UTC"
    return timezone_name


def _issued_at(order, locale: str, timezone_name: str) -> str:
    issued = getattr(order, "paid_at", None) or order.created_at
    if issued is None:
        return "-"
    issued = issued.replace(tzinfo=timezone.utc) if issued.tzinfo is None else issued
    if locale == "fa":
        tehran_time = issued.astimezone(ZoneInfo(_effective_timezone(locale, timezone_name))).replace(tzinfo=None)
        return jdatetime.datetime.fromgregorian(datetime=tehran_time).strftime("%Y/%m/%d %H:%M")
    timezone_name = _effective_timezone(locale, timezone_name)
    local_zone = ZoneInfo(timezone_name)
    local_time = issued.astimezone(local_zone)
    clock_zone = format_datetime(local_time, format="zzz", locale=LOCALE_TAGS[locale])
    return f"{format_datetime(local_time, format='medium', locale=LOCALE_TAGS[locale])} ({timezone_name}, {clock_zone})"


def invoice_fields(order, locale="fa", timezone_name="UTC") -> dict:
    locale = locale if locale in SUPPORTED_LOCALES else "fa"
    labels = INVOICE_TEXT[locale]
    subtotal = sum((Decimal(str(item.line_total)) for item in order.items), Decimal("0.00"))
    payment_status = labels["paid"]
    customer_lines = [order.customer_name]
    if order.customer_email:
        customer_lines.append(f"{labels['email']}: {order.customer_email}")
    customer_lines.extend((f"{labels['phone']}: {order.customer_phone}", f"{labels['address']}: {order.customer_address}"))
    return {
        "locale": locale,
        "labels": labels,
        "table_headers": [labels[key] for key in (("sum", "unit", "quantity", "product", "row") if locale == "fa" else ("row", "product", "quantity", "unit", "sum"))],
        "order_number": str(order.id),
        "invoice_number": order.invoice_number,
        "tracking_number": order.tracking_number,
        "issued_at": _issued_at(order, locale, timezone_name),
        "timezone": _effective_timezone(locale, timezone_name),
        "order_status": STATUS_LABELS[locale].get(order.status, order.status),
        "payment_status": payment_status,
        "subtotal": money(subtotal, locale),
        "total": money(order.total_amount, locale),
        "store_name": order.store.name,
        "customer_lines": customer_lines,
        "items": order.items,
    }


def render_invoice_pdf(order, locale="fa", timezone_name="UTC") -> bytes:
    fields = invoice_fields(order, locale, timezone_name)
    locale = fields["locale"]
    labels = fields["labels"]
    output = BytesIO()
    page_width, _ = A4
    margin = 16 * mm
    content_width = page_width - 2 * margin
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=order.invoice_number,
    )

    story = []

    header = Table(
        [[Paragraph("NAVA", STYLES["brand"]), _p(labels["title"], "doc_title", locale)]],
        colWidths=[content_width * 0.5, content_width * 0.5],
        hAlign="RIGHT" if locale == "fa" else "LEFT",
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(header)
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=LINE))
    story.append(Spacer(1, 5 * mm))

    story.append(_meta_row([
        (labels["invoice"], fields["invoice_number"]),
        (labels["order"], fields["order_number"]),
        (labels["tracking"], fields["tracking_number"]),
        (labels["issued"], fields["issued_at"]),
        (labels["timezone"], fields["timezone"]),
        (labels["status"], fields["order_status"]),
        (labels["payment"], fields["payment_status"]),
    ], content_width, locale))
    story.append(Spacer(1, 6 * mm))

    story.append(_p(labels["seller"], "section", locale))
    story.append(_p(fields["store_name"], "body", locale))
    story.append(Spacer(1, 5 * mm))

    story.append(_p(labels["customer"], "section", locale))
    for line in fields["customer_lines"]:
        story.append(_p(line, "body", locale))
    story.append(Spacer(1, 6 * mm))

    story.append(_p(labels["items"], "section", locale))
    story.append(_items_table(fields["items"], content_width, locale, fields["table_headers"]))
    story.append(Spacer(1, 6 * mm))

    totals = [
        [labels["subtotal"], fields["subtotal"]],
        [labels["total"], fields["total"]],
    ]
    totals_table = Table(
        [[_p(value, "total_value" if index == 1 else "meta_value", locale), _p(label, "total_label" if index == 1 else "meta_label", locale)] for index, (label, value) in enumerate(totals)],
        colWidths=[content_width * 0.5, content_width * 0.5],
        hAlign="RIGHT" if locale == "fa" else "LEFT",
    )
    totals_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (0, 1), (-1, 1), 0.8, TEAL_INK),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(totals_table)

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(FONT_REGULAR, 8.5)
        canvas.setFillColor(MUTED)
        text = rtl(labels["footer"]) if locale == "fa" else labels["footer"]
        canvas.drawCentredString(page_width / 2, 10 * mm, text)
        canvas.restoreState()

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()


