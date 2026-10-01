from decimal import Decimal
from datetime import datetime, timezone

from app.services.invoice_service import INVOICE_TEXT, _issued_at, invoice_fields, money, render_invoice_pdf, rtl


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
        self.id = 321
        self.tracking_number = "4821903357"
        self.created_at = datetime(2026, 9, 20, 14, 30, tzinfo=timezone.utc)
        self.paid_at = datetime(2026, 9, 20, 15, 30, tzinfo=timezone.utc)
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


def test_render_invoice_pdf_supports_all_locales():
    for locale in ("fa", "en", "es", "de", "fr"):
        pdf_bytes = render_invoice_pdf(_Order(), locale, "Europe/Berlin")
        assert pdf_bytes.startswith(b"%PDF")
        assert b"%%EOF" in pdf_bytes


def test_all_invoice_labels_are_localized_and_consumed_by_renderer():
    required_labels = {
        "title", "invoice", "order", "tracking", "issued", "timezone", "status",
        "payment", "seller", "customer", "items", "row", "product", "quantity",
        "unit", "sum", "subtotal", "total", "email", "phone", "address", "footer",
    }
    for locale in ("fa", "en", "es", "de", "fr"):
        order = _Order()
        fields = invoice_fields(order, locale, "Europe/Berlin")
        labels = INVOICE_TEXT[locale]
        assert required_labels <= labels.keys()
        assert fields["labels"] == labels
        assert fields["table_headers"] == [labels[key] for key in (("sum", "unit", "quantity", "product", "row") if locale == "fa" else ("row", "product", "quantity", "unit", "sum"))]
        assert fields["order_number"] == "321"
        assert fields["invoice_number"] == order.invoice_number
        assert fields["tracking_number"] == order.tracking_number
        assert fields["store_name"] == order.store.name
        assert fields["customer_lines"] == [
            order.customer_name,
            f"{labels['email']}: {order.customer_email}",
            f"{labels['phone']}: {order.customer_phone}",
            f"{labels['address']}: {order.customer_address}",
        ]
        assert fields["items"] == order.items
        assert fields["subtotal"] == money(Decimal("1540000"), locale)
        assert fields["payment_status"] == labels["paid"]
        assert fields["order_status"] == {
            "fa": "ارسال شد",
            "en": "Shipped",
            "es": "Enviado",
            "de": "Versendet",
            "fr": "Expédiée",
        }[locale]
        assert fields["timezone"] == ("Asia/Tehran" if locale == "fa" else "Europe/Berlin")
        assert render_invoice_pdf(order, locale, "Europe/Berlin").startswith(b"%PDF")


def test_persian_issued_date_is_jalali_tehran_time():
    assert _issued_at(_Order(), "fa", "America/Los_Angeles") == "1405/06/29 19:00"


def test_other_invoice_locales_use_customer_timezone():
    order = _Order()
    assert _issued_at(order, "en", "America/Los_Angeles") != _issued_at(order, "en", "Asia/Tokyo")


def test_non_persian_invoice_prints_timezone_and_uses_utc_fallback():
    order = _Order()
    fields = invoice_fields(order, "fr", "not-a-timezone")
    assert fields["timezone"] == "UTC"
    assert "UTC" in fields["issued_at"]


def test_persian_invoice_uses_payment_time_instead_of_checkout_time():
    order = _Order(created_at=datetime(2026, 9, 20, 14, 30, tzinfo=timezone.utc))
    assert _issued_at(order, "fa", "UTC").endswith("19:00")


def test_render_invoice_pdf_handles_missing_optional_fields():
    order = _Order(customer_email=None)
    pdf_bytes = render_invoice_pdf(order)
    assert pdf_bytes.startswith(b"%PDF")


def test_render_invoice_pdf_handles_many_items_across_pages():
    items = [_Item(f"کالای شماره {i}", 1, "10000") for i in range(60)]
    order = _Order(items=items, total_amount=Decimal("600000.00"))
    pdf_bytes = render_invoice_pdf(order)
    assert pdf_bytes.startswith(b"%PDF")