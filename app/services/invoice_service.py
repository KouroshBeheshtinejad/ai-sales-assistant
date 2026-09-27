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

from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

import arabic_reshaper
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


def money(value) -> str:
    """Formats an amount as plain (unshaped) text — callers route it through ``_p()``,
    which shapes it exactly once. Shaping this twice un-reverses the bidi reordering
    and renders as garbled/reversed Persian, so this must NOT call ``rtl()`` itself.
    """
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError):
        return f"{value} تومان"
    amount = amount.quantize(Decimal("1")) if amount == amount.to_integral_value() else amount.quantize(Decimal("0.01"))
    return f"{amount:,} تومان"


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


def _p(text, style):
    return Paragraph(rtl(text), STYLES[style])


def _meta_row(pairs):
    """A right-aligned label/value grid, e.g. 'شماره فاکتور  INV-000123'."""
    cells = []
    for label, value in pairs:
        cells.append([_p(value, "meta_value"), _p(label, "meta_label")])
    table = Table([[c for pair in cells for c in pair]], colWidths=None, hAlign="RIGHT")
    table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _items_table(items, width):
    # Physical column order is left-to-right; the *last* column ends up on the right
    # edge of the page, which is where a right-to-left reader expects the row number.
    header = [_p("جمع", "th"), _p("قیمت واحد", "th"), _p("تعداد", "th"), _p("کالا", "th"), _p("ردیف", "th")]
    rows = [header]
    for index, item in enumerate(items, start=1):
        rows.append([
            _p(money(item.line_total), "td"),
            _p(money(item.unit_price), "td"),
            _p(item.quantity, "td"),
            _p(item.product_name, "td_name"),
            _p(index, "td"),
        ])
    col_widths = [width * 0.20, width * 0.20, width * 0.12, width * 0.36, width * 0.12]
    table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="RIGHT")
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


def render_invoice_pdf(order) -> bytes:
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
        [[Paragraph("NAVA", STYLES["brand"]), _p("فاکتور فروش", "doc_title")]],
        colWidths=[content_width * 0.5, content_width * 0.5],
        hAlign="RIGHT",
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(header)
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=LINE))
    story.append(Spacer(1, 5 * mm))

    story.append(_meta_row([
        ("شماره فاکتور", order.invoice_number),
        ("کد رهگیری", order.tracking_number),
        ("تاریخ صدور", order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "-"),
        ("وضعیت سفارش", STATUS_LABELS_FA.get(order.status, order.status)),
    ]))
    story.append(Spacer(1, 6 * mm))

    story.append(_p("فروشنده", "section"))
    story.append(_p(order.store.name, "body"))
    story.append(Spacer(1, 5 * mm))

    story.append(_p("مشخصات مشتری", "section"))
    customer_lines = [order.customer_name]
    if order.customer_email:
        customer_lines.append(f"ایمیل: {order.customer_email}")
    customer_lines.append(f"تلفن: {order.customer_phone}")
    customer_lines.append(f"آدرس: {order.customer_address}")
    for line in customer_lines:
        story.append(_p(line, "body"))
    story.append(Spacer(1, 6 * mm))

    story.append(_p("اقلام سفارش", "section"))
    story.append(_items_table(order.items, content_width))
    story.append(Spacer(1, 6 * mm))

    total_row = Table(
        [[_p(money(order.total_amount), "total_value"), _p("جمع کل", "total_label")]],
        colWidths=[content_width * 0.5, content_width * 0.5],
        hAlign="RIGHT",
    )
    total_row.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, TEAL_INK),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(total_row)

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(FONT_REGULAR, 8.5)
        canvas.setFillColor(MUTED)
        text = rtl("این فاکتور توسط ناوا صادر شده است — دستیار فروش هوشمند فروشگاه‌های آنلاین")
        canvas.drawCentredString(page_width / 2, 10 * mm, text)
        canvas.restoreState()

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()


