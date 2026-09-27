from decimal import Decimal
from datetime import datetime, timezone

from app.services.invoice_service import money, render_invoice_pdf, rtl


class _Item:
    def __init__(self, name, qty, unit_price):
        self.product_name = name
        self.quantity = qty
        self.unit_price = Decimal(unit_price)
        self.line_total = Decimal(unit_price) * qty


class _Store:
    def __init__(self, name):
        self.name = name


class _Order:
    def __init__(self, **overrides):
        self.invoice_number = "INV-000123"
        self.tracking_number = "4821903357"
        self.created_at = datetime(2026, 9, 20, 14, 30, tzinfo=timezone.utc)
        self.status = "shipped"
        self.store = _Store("پوشاک آبی")
        self.customer_name = "علی رضایی"
        self.customer_email = "ali@example.com"
        self.customer_phone = "09120000000"
        self.customer_address = "تهران، خیابان ولیعصر، پلاک ۱۲"
        self.total_amount = Decimal("1540000.00")
        self.items = [
            _Item("هودی مشکی سایز L", 1, "890000"),
            _Item("شلوار جین آبی", 1, "650000"),
        ]
        for key, value in overrides.items():
            setattr(self, key, value)


def test_money_formats_whole_tomans_without_decimals():
    assert money(Decimal("890000.00")) == "890,000 تومان"


def test_money_keeps_decimals_when_not_whole():
    assert money(Decimal("890000.50")) == "890,000.50 تومان"


def test_money_does_not_pre_shape_text():
    # money() must return plain text: shaping happens exactly once, in the Paragraph
    # helper that consumes it. Shaping it here too would double-reverse the Persian
    # word and reproduce the original "black squares / reversed text" bug.
    assert money(Decimal("1000.00")) == "1,000 تومان"


def test_rtl_is_a_no_op_for_plain_latin_text():
    assert rtl("INV-000123") == "INV-000123"


def test_rtl_shapes_persian_text_into_presentation_forms():
    shaped = rtl("تومان")
    # A shaped+reordered string is not equal to the original logical string, and every
    # character in it comes from the Arabic Presentation Forms block reportlab can draw.
    assert shaped != "تومان"
    assert all(0xFB50 <= ord(ch) <= 0xFEFF or ch in " " for ch in shaped)


def test_render_invoice_pdf_returns_a_valid_pdf():
    pdf_bytes = render_invoice_pdf(_Order())
    assert pdf_bytes.startswith(b"%PDF")
    assert b"%%EOF" in pdf_bytes


def test_render_invoice_pdf_embeds_the_persian_font():
    pdf_bytes = render_invoice_pdf(_Order())
    # Confirms the Persian-capable font actually made it into the document rather than
    # silently falling back to Helvetica (which cannot render Persian at all).
    assert b"Vazirmatn" in pdf_bytes


def test_render_invoice_pdf_handles_missing_optional_fields():
    order = _Order(customer_email=None)
    pdf_bytes = render_invoice_pdf(order)
    assert pdf_bytes.startswith(b"%PDF")


def test_render_invoice_pdf_handles_many_items_across_pages():
    items = [_Item(f"کالای شماره {i}", 1, "10000") for i in range(60)]
    order = _Order(items=items, total_amount=Decimal("600000.00"))
    pdf_bytes = render_invoice_pdf(order)
    assert pdf_bytes.startswith(b"%PDF")