import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.database import Base, get_db
from app.db.models import AuditLog, FAQ, KnowledgeBaseEntry, Order, Payment, Product, Store, StoreMembership, StorePaymentAccount, User
from app.main import app
from app.services.payment_service import (
    MockPaymentProvider,
    PaymentAccountContext,
    PaymentService,
    PaymentProviderNotConfigured,
    ZarinpalPaymentProvider,
    get_payment_provider,
    payment_provider_registry,
)
from app.services.audit_service import content_audit_state
from app.security.payment_credentials import decrypt_payment_credential, encrypt_payment_credential


@pytest.fixture()
def payment_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = session_factory()
    user = User(email="payments@example.com", password_hash=hash_password("StrongPass123!"), is_verified=True)
    db.add(user)
    db.flush()
    store = Store(name="Payment Store", owner_id=user.id)
    db.add(store)
    db.flush()
    product = Product(name="Payment Product", price=Decimal("12.50"), stock=2, store_id=store.id, is_active=True)
    db.add(product)
    support_user = User(email="support-target@example.com", password_hash=hash_password("StrongPass123!"), is_verified=True)
    db.add(support_user)
    db.flush()
    other_store = Store(name="Other Store", owner_id=support_user.id)
    db.add(other_store)
    store_admin = User(
        email="store-admin@example.com",
        password_hash=hash_password("StrongPass123!"),
        role="store_admin",
        approval_status="active",
        is_verified=True,
    )
    db.add(store_admin)
    db.flush()
    db.add(StoreMembership(store_id=store.id, user_id=store_admin.id, status="approved"))
    applicant = User(
        email="store-admin-applicant@example.com",
        password_hash=hash_password("StrongPass123!"),
        role="store_admin",
        approval_status="pending",
        is_verified=True,
    )
    db.add(applicant)
    db.flush()
    membership_request = StoreMembership(store_id=store.id, user_id=applicant.id, status="pending")
    db.add(membership_request)
    db.commit()
    context = {
        "user_id": user.id,
        "store_id": store.id,
        "product_id": product.id,
        "token": create_access_token(str(user.id)),
        "support_user_id": support_user.id,
        "support_token": create_access_token(str(support_user.id)),
        "other_store_id": other_store.id,
        "store_admin_id": store_admin.id,
        "store_admin_token": create_access_token(str(store_admin.id)),
        "admin_applicant_id": applicant.id,
        "admin_membership_id": membership_request.id,
    }
    db.close()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, context
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def auth_headers(context):
    return {"Authorization": f"Bearer {context['token']}"}


def test_content_audit_snapshot_does_not_store_raw_answer():
    faq = FAQ(question="Shipping?", answer="Private content", store_id=1)

    snapshot = content_audit_state(faq)

    assert snapshot["label"] == "Shipping?"
    assert snapshot["content_sha256"]
    assert "Private content" not in str(snapshot)


def create_order(client, context):
    cart = client.post(
        f"/cart/stores/{context['store_id']}/items",
        headers=auth_headers(context),
        json={"product_id": context["product_id"], "quantity": 1},
    )
    assert cart.status_code == 200
    order = client.post(
        f"/orders/stores/{context['store_id']}",
        headers=auth_headers(context),
        json={"customer_name": "Ali", "customer_phone": "0912", "customer_address": "Tehran"},
    )
    assert order.status_code == 201
    created = order.json()
    selected_provider = os.getenv("PAYMENT_PROVIDER", "disabled").strip().casefold()
    if selected_provider in {"mock", "zarinpal"}:
        db = next(app.dependency_overrides[get_db]())
        try:
            store = db.get(Store, context["store_id"])
            store.payment_provider = selected_provider
            account = db.query(StorePaymentAccount).filter_by(
                store_id=store.id,
                provider=selected_provider,
            ).one_or_none()
            if account is None:
                db.add(StorePaymentAccount(
                    store_id=store.id,
                    provider=selected_provider,
                    external_account_id="test-merchant" if selected_provider == "zarinpal" else "test-account",
                    status="active",
                    country_code="IR",
                    currency="IRT",
                ))
            db.commit()
        finally:
            db.close()
    assert created["tracking_number"] is None
    assert created["invoice_number"] is None
    assert client.get(f"/orders/{created['id']}/invoice", headers=auth_headers(context)).status_code == 404
    seller_orders = client.get(
        f"/seller/orders/stores/{context['store_id']}",
        headers=auth_headers(context),
    )
    assert seller_orders.status_code == 200
    assert seller_orders.json() == []
    return created


@pytest.mark.parametrize("provider", [None, "disabled"])
def test_payment_requires_configured_provider(payment_context, monkeypatch, provider):
    client, context = payment_context
    if provider is None:
        monkeypatch.delenv("PAYMENT_PROVIDER", raising=False)
    else:
        monkeypatch.setenv("PAYMENT_PROVIDER", provider)
    order = create_order(client, context)

    response = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-disabled-1"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Payment is not configured for this Store"


def test_production_rejects_mock_payment_provider(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")

    with pytest.raises(PaymentProviderNotConfigured):
        get_payment_provider()


def test_zarinpal_uses_rials_and_v4_response_envelope(monkeypatch):
    monkeypatch.setenv("PAYMENT_SECRET_ZARINPAL_TEST", "merchant-id")
    monkeypatch.setenv("PAYMENT_CALLBACK_URL", "https://nava.example/api/payments/callback")
    provider = ZarinpalPaymentProvider(PaymentAccountContext(
        provider="zarinpal", store_id=1, account_id=1,
        external_account_id=None, credential_reference="ZARINPAL_TEST",
        country_code="IR", currency="IRT",
    ))
    requests = []
    responses = iter((
        {"data": {"code": 100, "authority": "A-authority"}, "errors": []},
        {"data": {"code": 101, "ref_id": 12345}, "errors": []},
    ))

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(next(responses)).encode()

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr("app.services.payment_service.urllib_request.urlopen", fake_urlopen)

    created = provider.create_payment(amount=Decimal("12500.00"), currency="IRT", order_id=7)
    verified = provider.verify_payment(amount=Decimal("12500.00"), currency="IRT", authority="A-authority")

    assert created == {
        "authority": "A-authority",
        "payment_url": "https://payment.zarinpal.com/pg/StartPay/A-authority",
    }
    assert verified == {"transaction_id": "12345"}
    request_payloads = [json.loads(request.data) for request, _timeout in requests]
    assert request_payloads[0]["amount"] == 125000
    assert request_payloads[0]["currency"] == "IRR"
    assert request_payloads[1]["amount"] == 125000
    assert all(timeout == 15 for _request, timeout in requests)


@pytest.mark.parametrize(
    ("gateway_status", "expected_status"),
    [
        ("VERIFIED", "paid"),
        ("PAID", "paid"),
        ("IN_BANK", "pending"),
        ("FAILED", "failed"),
        ("REVERSED", "cancelled"),
        ("UNRECOGNIZED", "unknown"),
    ],
)
def test_zarinpal_inquiry_maps_statuses_with_store_credential(monkeypatch, gateway_status, expected_status):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("PAYMENT_CREDENTIAL_ENCRYPTION_KEY", key)
    monkeypatch.setenv("PAYMENT_CALLBACK_URL", "https://nava.example/api/payments/callback")
    merchant_id = "11111111-1111-4111-8111-111111111111"
    context = PaymentAccountContext(
        provider="zarinpal",
        store_id=17,
        account_id=23,
        external_account_id=None,
        credential_reference=None,
        country_code="IR",
        currency="IRT",
        credential_ciphertext=encrypt_payment_credential(merchant_id),
    )
    provider = ZarinpalPaymentProvider(context)
    payloads = []
    monkeypatch.setattr(
        provider,
        "_post",
        lambda path, payload: payloads.append((path, payload)) or {"data": {"status": gateway_status}},
    )

    assert provider.get_status(authority="A-authority", currency="IRT") == expected_status
    assert payloads == [("inquiry.json", {"merchant_id": merchant_id, "authority": "A-authority"})]


def test_store_credentials_are_encrypted_unique_and_never_returned(payment_context, monkeypatch, caplog):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_CALLBACK_URL", "https://nava.example/api/payments/callback")
    monkeypatch.setenv("PAYMENT_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    merchant_one = "11111111-1111-4111-8111-111111111111"
    merchant_two = "22222222-2222-4222-8222-222222222222"

    def configure(store_id, headers, merchant_id):
        return client.put(
            f"/stores/{store_id}/payment-settings",
            headers=headers,
            json={"country_code": "IR", "currency": "IRT", "provider": "zarinpal", "merchant_id": merchant_id},
        )

    first = configure(context["store_id"], auth_headers(context), merchant_one)
    assert first.status_code == 200
    assert merchant_one not in first.text
    assert "credential_ciphertext" not in first.json()
    assert "merchant_id" not in first.json()

    duplicate = configure(
        context["other_store_id"],
        {"Authorization": f"Bearer {context['support_token']}"},
        merchant_one,
    )
    assert duplicate.status_code == 409
    assert merchant_one not in duplicate.text

    second = configure(
        context["other_store_id"],
        {"Authorization": f"Bearer {context['support_token']}"},
        merchant_two,
    )
    assert second.status_code == 200
    assert merchant_two not in second.text
    assert merchant_one not in caplog.text
    assert merchant_two not in caplog.text

    db = next(app.dependency_overrides[get_db]())
    try:
        accounts = db.query(StorePaymentAccount).filter_by(provider="zarinpal").all()
        assert len(accounts) == 2
        assert {decrypt_payment_credential(account.credential_ciphertext) for account in accounts} == {merchant_one, merchant_two}
        assert all(account.credential_reference is None for account in accounts)
    finally:
        db.close()


def test_database_rejects_duplicate_store_credential_fingerprints(payment_context):
    _client, context = payment_context
    db = next(app.dependency_overrides[get_db]())
    try:
        fingerprint = "a" * 64
        db.add_all((
            StorePaymentAccount(
                store_id=context["store_id"], provider="zarinpal", status="active",
                country_code="IR", currency="IRT", credential_fingerprint=fingerprint,
            ),
            StorePaymentAccount(
                store_id=context["other_store_id"], provider="zarinpal", status="active",
                country_code="IR", currency="IRT", credential_fingerprint=fingerprint,
            ),
        ))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_zarinpal_payment_uses_snapshotted_store_credential_and_finalizes_once(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PAYMENT_PROVIDER", "zarinpal")
    monkeypatch.setenv("PAYMENT_CALLBACK_URL", "https://nava.example/api/payments/callback")
    monkeypatch.setenv("PAYMENT_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr("app.services.payment_service.notify_payment_success", lambda *_args: None)
    merchant_id = "11111111-1111-4111-8111-111111111111"
    order = create_order(client, context)
    settings = client.put(
        f"/stores/{context['store_id']}/payment-settings",
        headers=auth_headers(context),
        json={"country_code": "IR", "currency": "IRT", "provider": "zarinpal", "merchant_id": merchant_id},
    )
    assert settings.status_code == 200

    responses = iter((
        {"data": {"code": 100, "authority": "A-order-authority"}, "errors": []},
        {"data": {"status": "UNRECOGNIZED"}, "errors": []},
        {"data": {"status": "PAID"}, "errors": []},
        {"data": {"code": 101, "ref_id": 12345}, "errors": []},
        {"data": {"code": 100, "message": "Reversed"}, "errors": []},
    ))
    request_payloads = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(next(responses)).encode()

    def fake_urlopen(request, timeout):
        request_payloads.append(json.loads(request.data))
        return FakeResponse()

    monkeypatch.setattr("app.services.payment_service.urllib_request.urlopen", fake_urlopen)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "zarinpal-create-once"},
    )
    assert created.status_code == 201
    assert request_payloads[0]["merchant_id"] == merchant_id
    reconciled = client.post(f"/payments/{created.json()['id']}/reconcile", headers=auth_headers(context))
    assert reconciled.status_code == 200
    assert reconciled.json()["status"] == "pending"
    duplicate_create = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "zarinpal-create-retry"},
    )
    assert duplicate_create.status_code == 201
    assert duplicate_create.json()["id"] == created.json()["id"]
    assert len(request_payloads) == 2

    db = next(app.dependency_overrides[get_db]())
    try:
        account = db.query(StorePaymentAccount).filter_by(store_id=context["store_id"], provider="zarinpal").one()
        account.credential_ciphertext = encrypt_payment_credential("33333333-3333-4333-8333-333333333333")
        db.commit()
    finally:
        db.close()

    reconciled_paid = client.post(f"/payments/{created.json()['id']}/reconcile", headers=auth_headers(context))
    assert reconciled_paid.status_code == 200
    assert reconciled_paid.json()["status"] == "paid"
    verified = client.post(
        f"/payments/{created.json()['id']}/verify",
        headers=auth_headers(context),
        json={"authority": created.json()["authority"]},
    )
    repeated = client.post(
        f"/payments/{created.json()['id']}/verify",
        headers=auth_headers(context),
        json={"authority": created.json()["authority"]},
    )
    assert verified.status_code == repeated.status_code == 200
    assert verified.json()["status"] == "paid"
    assert request_payloads[3]["merchant_id"] == merchant_id
    assert len(request_payloads) == 4

    refund_headers = {**auth_headers(context), "Idempotency-Key": "zarinpal-full-reverse"}
    partial_refund = client.post(
        f"/payments/{created.json()['id']}/refunds",
        headers={**auth_headers(context), "Idempotency-Key": "zarinpal-partial-reverse"},
        json={"amount": "6.25"},
    )
    assert partial_refund.status_code == 400
    assert len(request_payloads) == 4

    db = next(app.dependency_overrides[get_db]())
    try:
        stored_payment = db.get(Payment, created.json()["id"])
        stored_payment.paid_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=31)
        db.commit()
    finally:
        db.close()
    expired_refund = client.post(
        f"/payments/{created.json()['id']}/refunds",
        headers={**auth_headers(context), "Idempotency-Key": "zarinpal-expired-reverse"},
        json={"amount": "12.50"},
    )
    assert expired_refund.status_code == 400
    assert len(request_payloads) == 4
    db = next(app.dependency_overrides[get_db]())
    try:
        db.get(Payment, created.json()["id"]).paid_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    finally:
        db.close()

    refund = client.post(
        f"/payments/{created.json()['id']}/refunds",
        headers=refund_headers,
        json={"amount": "12.50"},
    )
    repeated_refund = client.post(
        f"/payments/{created.json()['id']}/refunds",
        headers=refund_headers,
        json={"amount": "12.50"},
    )
    assert refund.status_code == repeated_refund.status_code == 201
    assert refund.json()["id"] == repeated_refund.json()["id"]
    assert request_payloads[4] == {"merchant_id": merchant_id, "authority": "A-order-authority"}
    assert len(request_payloads) == 5

    db = next(app.dependency_overrides[get_db]())
    try:
        stored_order = db.get(Order, order["id"])
        stored_payment = db.get(Payment, created.json()["id"])
        assert stored_payment.status == "refunded"
        assert stored_order.paid_at is not None
        assert stored_order.tracking_number
        assert stored_order.invoice_number
        assert db.get(Product, context["product_id"]).stock == 1
        assert len([item for item in stored_payment.transactions if item.transaction_type == "verification"]) == 1
        assert len([item for item in stored_payment.transactions if item.transaction_type == "refund"]) == 1
    finally:
        db.close()


def test_negative_and_repeated_callbacks_do_not_double_finalize(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "callback-create"},
    )
    payment = created.json()
    verification_calls = 0
    original_verify = MockPaymentProvider.verify_payment

    def counted_verify(self, *, amount, currency, authority):
        nonlocal verification_calls
        verification_calls += 1
        return original_verify(self, amount=amount, currency=currency, authority=authority)

    monkeypatch.setattr(MockPaymentProvider, "verify_payment", counted_verify)
    negative = client.get(
        f"/payments/callback?Authority={payment['authority']}&Status=NOK",
        follow_redirects=False,
    )
    assert negative.status_code == 303
    assert "payment=failed" in negative.headers["location"]
    db = next(app.dependency_overrides[get_db]())
    try:
        stored_order = db.get(Order, order["id"])
        stored_payment = db.get(Payment, payment["id"])
        assert stored_payment.status == "pending"
        assert stored_order.paid_at is None
        assert stored_order.tracking_number is None
        assert stored_order.invoice_number is None
        assert db.get(Product, context["product_id"]).stock == 2
    finally:
        db.close()

    for _ in range(2):
        success = client.get(
            f"/payments/callback?Authority={payment['authority']}&Status=OK",
            follow_redirects=False,
        )
        assert success.status_code == 303
        assert "payment=success" in success.headers["location"]
    repeated_verify = client.post(
        f"/payments/{payment['id']}/verify",
        headers=auth_headers(context),
        json={"authority": payment["authority"]},
    )
    assert repeated_verify.status_code == 200
    assert verification_calls == 1

    db = next(app.dependency_overrides[get_db]())
    try:
        stored_order = db.get(Order, order["id"])
        stored_payment = db.get(Payment, payment["id"])
        assert stored_order.paid_at is not None
        assert stored_order.tracking_number
        assert stored_order.invoice_number
        assert db.get(Product, context["product_id"]).stock == 1
        assert len([item for item in stored_payment.transactions if item.transaction_type == "verification"]) == 1
    finally:
        db.close()


def test_failed_zarinpal_verification_never_finalizes_order(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "zarinpal")
    monkeypatch.setenv("PAYMENT_CALLBACK_URL", "https://nava.example/api/payments/callback")
    monkeypatch.setenv("PAYMENT_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    order = create_order(client, context)
    merchant_id = "11111111-1111-4111-8111-111111111111"
    settings = client.put(
        f"/stores/{context['store_id']}/payment-settings",
        headers=auth_headers(context),
        json={"country_code": "IR", "currency": "IRT", "provider": "zarinpal", "merchant_id": merchant_id},
    )
    assert settings.status_code == 200
    responses = iter((
        {"data": {"code": 100, "authority": "A-failed-authority"}, "errors": []},
        {"data": {"code": -51, "message": "Payment not successful"}, "errors": []},
    ))

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(next(responses)).encode()

    monkeypatch.setattr(
        "app.services.payment_service.urllib_request.urlopen",
        lambda request, timeout: FakeResponse(),
    )
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "zarinpal-failed-create"},
    )
    failed = client.post(
        f"/payments/{created.json()['id']}/verify",
        headers=auth_headers(context),
        json={"authority": created.json()["authority"]},
    )
    assert failed.status_code == 400
    db = next(app.dependency_overrides[get_db]())
    try:
        stored_order = db.get(Order, order["id"])
        stored_payment = db.get(Payment, created.json()["id"])
        assert stored_payment.status == "failed"
        assert stored_order.paid_at is None
        assert stored_order.tracking_number is None
        assert stored_order.invoice_number is None
        assert db.get(Product, context["product_id"]).stock == 2
    finally:
        db.close()


def test_payment_with_cross_store_account_snapshot_cannot_be_verified(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "cross-store-create"},
    )
    db = next(app.dependency_overrides[get_db]())
    try:
        stored_payment = db.get(Payment, created.json()["id"])
        stored_payment.provider_context = {
            **stored_payment.provider_context,
            "store_id": context["other_store_id"],
        }
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/payments/{created.json()['id']}/verify",
        headers=auth_headers(context),
        json={"authority": created.json()["authority"]},
    )
    assert response.status_code == 503
    db = next(app.dependency_overrides[get_db]())
    try:
        assert db.get(Payment, created.json()["id"]).status == "pending"
        assert db.get(Order, order["id"]).paid_at is None
    finally:
        db.close()


def test_zarinpal_rejects_fractional_rial_amount(monkeypatch):
    monkeypatch.setenv("PAYMENT_SECRET_ZARINPAL_TEST", "merchant-id")
    monkeypatch.setenv("PAYMENT_CALLBACK_URL", "https://nava.example/api/payments/callback")
    provider = ZarinpalPaymentProvider(PaymentAccountContext(
        provider="zarinpal", store_id=1, account_id=1,
        external_account_id=None, credential_reference="ZARINPAL_TEST",
        country_code="IR", currency="IRT",
    ))

    with pytest.raises(ValueError, match="whole rial"):
        provider.create_payment(amount=Decimal("1.25"), currency="IRT", order_id=7)


def test_store_payment_settings_are_conditional_and_never_return_account_ids(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_CALLBACK_URL", "https://nava.example/api/payments/callback")
    monkeypatch.setenv("PAYMENT_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("PAYMENT_SECRET_ZARINPAL_STORE_ONE", "merchant-store-one")
    headers = auth_headers(context)
    initial = client.get(f"/stores/{context['store_id']}/payment-settings", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["provider"] == "disabled"

    zarinpal = client.put(
        f"/stores/{context['store_id']}/payment-settings",
        headers=headers,
        json={
            "country_code": "IR",
            "currency": "IRT",
            "provider": "zarinpal",
            "credential_reference": "ZARINPAL_STORE_ONE",
        },
    )
    assert zarinpal.status_code == 200
    assert zarinpal.json()["status"] == "active"
    assert zarinpal.json()["account_configured"] is True
    assert "external_account_id" not in zarinpal.json()
    assert "credential_reference" not in zarinpal.json()
    assert "ZARINPAL_STORE_ONE" not in zarinpal.text

    duplicate_legacy_credential = client.put(
        f"/stores/{context['other_store_id']}/payment-settings",
        headers={"Authorization": f"Bearer {context['support_token']}"},
        json={
            "country_code": "IR",
            "currency": "IRT",
            "provider": "zarinpal",
            "credential_reference": "ZARINPAL_STORE_ONE",
        },
    )
    assert duplicate_legacy_credential.status_code == 409
    assert "merchant-store-one" not in duplicate_legacy_credential.text

    international = client.put(
        f"/stores/{context['store_id']}/payment-settings",
        headers=headers,
        json={
            "country_code": "US",
            "currency": "USD",
            "provider": "stripe_connect",
            "external_account_id": "acct_store_one",
        },
    )
    assert international.status_code == 200
    assert international.json()["provider"] == "stripe_connect"
    assert international.json()["status"] == "pending"
    assert international.json()["adapter_available"] is False
    assert "merchant-store-one" not in international.text

    db = next(app.dependency_overrides[get_db]())
    try:
        store = db.get(Store, context["store_id"])
        assert store.country_code == "US"
        assert store.currency == "USD"
        assert store.payment_provider == "stripe_connect"
        assert db.query(StorePaymentAccount).filter_by(store_id=store.id, provider="zarinpal").one().credential_reference == "ZARINPAL_STORE_ONE"
    finally:
        db.close()


def test_legacy_zarinpal_account_requires_settings_resave_for_fingerprint(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_CALLBACK_URL", "https://nava.example/api/payments/callback")
    monkeypatch.setenv("PAYMENT_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("PAYMENT_SECRET_LEGACY_STORE", "legacy-merchant-credential")
    db = next(app.dependency_overrides[get_db]())
    try:
        store = db.get(Store, context["store_id"])
        store.payment_provider = "zarinpal"
        db.add(StorePaymentAccount(
            store_id=store.id,
            provider="zarinpal",
            credential_reference="LEGACY_STORE",
            status="active",
            country_code="IR",
            currency="IRT",
        ))
        db.commit()
    finally:
        db.close()

    headers = auth_headers(context)
    settings = client.get(f"/stores/{context['store_id']}/payment-settings", headers=headers)
    assert settings.status_code == 200
    assert settings.json()["status"] == "pending"

    resaved = client.put(
        f"/stores/{context['store_id']}/payment-settings",
        headers=headers,
        json={"country_code": "IR", "currency": "IRT", "provider": "zarinpal"},
    )
    assert resaved.status_code == 200
    assert resaved.json()["status"] == "active"
    db = next(app.dependency_overrides[get_db]())
    try:
        account = db.query(StorePaymentAccount).filter_by(store_id=context["store_id"], provider="zarinpal").one()
        assert account.credential_fingerprint
    finally:
        db.close()


def test_two_stores_select_distinct_payment_adapters_and_accounts(payment_context, monkeypatch):
    _client, context = payment_context
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PAYMENT_PROVIDER", "disabled")

    class AccountBoundProvider:
        name = "stripe_connect"

        def __init__(self, account):
            self.account = account

        def create_payment(self, *, amount, currency, order_id, callback_url=None):
            return {"authority": f"{self.account.external_account_id}-{order_id}", "payment_url": "https://checkout.example.test"}

        def verify_payment(self, *, amount, currency, authority):
            return {"transaction_id": f"tx-{authority}"}

        def get_status(self, *, authority, currency):
            return "pending"

        def refund(self, *, transaction_id, amount, currency):
            return {"status": "refunded"}

    payment_provider_registry.register("stripe_connect", lambda account: AccountBoundProvider(account))
    db = next(app.dependency_overrides[get_db]())
    try:
        first_store = db.get(Store, context["store_id"])
        second_store = db.get(Store, context["other_store_id"])
        first_store.payment_provider = "mock"
        second_store.payment_provider = "stripe_connect"
        second_store.country_code = "US"
        second_store.currency = "USD"
        first_account = StorePaymentAccount(
            store_id=first_store.id, provider="mock", external_account_id="mock-account-one",
            status="active", country_code="IR", currency="IRT",
        )
        second_account = StorePaymentAccount(
            store_id=second_store.id, provider="stripe_connect", external_account_id="acct_connected_two",
            status="active", country_code="US", currency="USD",
        )
        db.add_all([first_account, second_account])
        first_order = Order(
            user_id=context["user_id"], store_id=first_store.id, status="pending",
            customer_name="One", customer_phone="0912", customer_address="Tehran",
            total_amount=Decimal("12500.00"), currency="IRT",
        )
        second_order = Order(
            user_id=context["support_user_id"], store_id=second_store.id, status="pending",
            customer_name="Two", customer_phone="+12025550123", customer_address="New York",
            total_amount=Decimal("12.50"), currency="USD",
        )
        db.add_all([first_order, second_order])
        db.commit()

        first_payment = PaymentService.create_payment(db, first_order.id, "store-one-key", user_id=context["user_id"])
        second_payment = PaymentService.create_payment(db, second_order.id, "store-two-key", user_id=context["support_user_id"])

        assert first_payment.provider == "mock"
        assert first_payment.currency == "IRT"
        assert first_payment.provider_context["external_account_id"] == "mock-account-one"
        assert second_payment.provider == "stripe_connect"
        assert second_payment.currency == "USD"
        assert second_payment.provider_context["external_account_id"] == "acct_connected_two"
    finally:
        db.close()
        payment_provider_registry.unregister("stripe_connect")


def test_reconciliation_expires_payment_and_allows_a_safe_retry(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "reconcile-expiry-1"},
    )
    payment = created.json()
    monkeypatch.setattr(MockPaymentProvider, "get_status", lambda self, *, authority, currency: "expired")

    reconciled = client.post(
        f"/payments/{payment['id']}/reconcile",
        headers=auth_headers(context),
    )

    assert reconciled.status_code == 200
    assert reconciled.json()["status"] == "expired"
    retry = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "reconcile-expiry-2"},
    )
    assert retry.status_code == 201
    assert retry.json()["id"] != payment["id"]
    assert client.get(f"/orders/{order['id']}", headers=auth_headers(context)).status_code == 404


def test_refund_is_idempotent_and_cannot_exceed_paid_amount(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "refund-payment-create"},
    )
    payment = created.json()
    verified = client.post(
        f"/payments/{payment['id']}/verify",
        headers=auth_headers(context),
        json={"authority": payment["authority"]},
    )
    assert verified.status_code == 200

    headers = {**auth_headers(context), "Idempotency-Key": "refund-half"}
    first = client.post(f"/payments/{payment['id']}/refunds", headers=headers, json={"amount": "6.25"})
    repeated = client.post(f"/payments/{payment['id']}/refunds", headers=headers, json={"amount": "6.25"})
    assert first.status_code == 201
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]

    excess = client.post(
        f"/payments/{payment['id']}/refunds",
        headers={**auth_headers(context), "Idempotency-Key": "refund-overflow"},
        json={"amount": "6.26"},
    )
    assert excess.status_code == 400
    db = next(app.dependency_overrides[get_db]())
    try:
        stored_payment = db.get(Payment, payment["id"])
        refunds = [item for item in stored_payment.transactions if item.transaction_type == "refund"]
        assert len(refunds) == 1
        assert refunds[0].status == "refunded"
    finally:
        db.close()


def test_god_role_is_server_managed_and_support_is_read_only(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("GOD_USER_EMAIL", "payments@example.com")
    god_headers = auth_headers(context)

    profile = client.get("/api/auth/me", headers=god_headers)
    assert profile.status_code == 200
    assert profile.json()["role"] == "god"
    stores = client.get("/api/stores/", headers=god_headers)
    assert {store["id"] for store in stores.json()} == {context["store_id"], context["other_store_id"]}
    platform_stores = client.get("/api/admin/stores", headers=god_headers)
    assert platform_stores.status_code == 200
    assert {store["id"] for store in platform_stores.json()} == {context["store_id"], context["other_store_id"]}
    overview = client.get("/api/admin/system/overview", headers=god_headers)
    assert overview.status_code == 200
    assert overview.json()["database_status"] == "ok"
    assert overview.json()["users"]["total"] >= 4
    assert client.get(
        "/api/admin/system/overview",
        headers={"Authorization": f"Bearer {context['support_token']}"},
    ).status_code == 403
    platform_products = client.get("/api/admin/products", headers=god_headers)
    assert platform_products.status_code == 200
    assert any(product["id"] == context["product_id"] for product in platform_products.json())
    database_users = client.get("/api/admin/database/users", headers=god_headers)
    assert database_users.status_code == 200
    inspected_user = client.get(
        f"/api/admin/database/users/{context['user_id']}", headers=god_headers
    )
    assert inspected_user.status_code == 200
    assert "password_hash" not in inspected_user.json()

    promoted = client.patch(
        f"/api/admin/users/{context['support_user_id']}/role",
        headers=god_headers,
        json={"role": "support"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "support"
    approval = client.patch(
        f"/api/admin/users/{context['support_user_id']}/approval",
        headers=god_headers,
        json={"status": "active"},
    )
    assert approval.status_code == 200

    db = next(app.dependency_overrides[get_db]())
    try:
        support = db.get(User, context["support_user_id"])
        support_headers = {"Authorization": f"Bearer {create_access_token(str(support.id), support.token_version)}"}
    finally:
        db.close()
    assert client.get("/api/admin/database/users", headers=support_headers).status_code == 403
    audit_logs = client.get("/api/admin/audit-logs", headers=god_headers)
    assert audit_logs.status_code == 200
    role_event = next(
        item
        for item in audit_logs.json()
        if item["action"] == "user.role_changed"
        and item["resource_id"] == str(context["support_user_id"])
    )
    assert role_event["after_state"]["role"] == "support"
    assert "password_hash" not in str(role_event)
    assert client.get("/api/admin/orders", headers=support_headers).status_code == 200
    assert client.get("/api/admin/users", headers=support_headers).status_code == 403
    assert client.get("/api/admin/audit-logs", headers=support_headers).status_code == 403
    assert client.patch(
        f"/api/admin/users/{context['user_id']}/role",
        headers=support_headers,
        json={"role": "store_owner"},
    ).status_code == 403


def test_store_admin_is_limited_to_approved_store_membership(payment_context):
    client, context = payment_context
    headers = {"Authorization": f"Bearer {context['store_admin_token']}"}
    stores = client.get("/api/stores/", headers=headers)
    assert stores.status_code == 200
    assert [item["id"] for item in stores.json()] == [context["store_id"]]
    assert client.get(f"/api/stores/{context['other_store_id']}", headers=headers).status_code == 404
    assert client.put(
        f"/api/stores/{context['store_id']}",
        headers=headers,
        json={"name": "Authorized admin rename"},
    ).status_code == 200
    assert client.put(
        f"/api/stores/{context['other_store_id']}",
        headers=headers,
        json={"name": "Cross-store rename"},
    ).status_code == 404


def test_store_membership_role_is_authoritative_per_store(payment_context):
    client, context = payment_context
    headers = {"Authorization": f"Bearer {context['store_admin_token']}"}
    db = next(app.dependency_overrides[get_db]())
    try:
        member = db.get(User, context["store_admin_id"])
        member.role = "customer"
        db.query(StoreMembership).filter_by(
            user_id=member.id,
            store_id=context["store_id"],
        ).one().role = "store_viewer"
        db.add(
            StoreMembership(
                store_id=context["other_store_id"],
                user_id=member.id,
                role="store_admin",
                status="approved",
            )
        )
        db.add(FAQ(question="Question", answer="Answer", store_id=context["store_id"]))
        db.add(
            KnowledgeBaseEntry(
                title="Policy", content="Content", store_id=context["store_id"]
            )
        )
        db.commit()
    finally:
        db.close()

    assert client.get(
        f"/api/products/?store_id={context['store_id']}", headers=headers
    ).status_code == 200
    assert client.post(
        "/api/products/",
        headers=headers,
        json={"store_id": context["store_id"], "name": "Blocked", "price": 1},
    ).status_code == 404
    assert client.post(
        "/api/products/",
        headers=headers,
        json={"store_id": context["other_store_id"], "name": "Allowed", "price": 1},
    ).status_code == 200
    assert client.get(
        f"/api/stores/{context['store_id']}/faqs", headers=headers
    ).status_code == 200
    assert client.post(
        f"/api/stores/{context['store_id']}/faqs",
        headers=headers,
        json={"question": "Blocked", "answer": "Blocked"},
    ).status_code == 404
    assert client.get(
        f"/api/stores/{context['store_id']}/knowledge", headers=headers
    ).status_code == 200
    assert client.post(
        f"/api/stores/{context['store_id']}/knowledge",
        headers=headers,
        json={"title": "Blocked", "content": "Blocked"},
    ).status_code == 404


def test_owner_can_manage_member_roles_and_revoke_store_access(payment_context):
    client, context = payment_context
    owner_headers = auth_headers(context)
    added = client.post(
        f"/api/stores/{context['store_id']}/members",
        headers=owner_headers,
        json={"email": "support-target@example.com", "role": "store_manager"},
    )
    assert added.status_code == 201
    assert added.json()["role"] == "store_manager"
    assert added.json()["status"] == "approved"
    membership_id = added.json()["id"]

    members = client.get(f"/api/stores/{context['store_id']}/members", headers=owner_headers)
    assert members.status_code == 200
    assert any(item["id"] == membership_id for item in members.json())
    assert client.post(
        f"/api/stores/{context['other_store_id']}/members",
        headers=owner_headers,
        json={"email": "payments@example.com", "role": "store_viewer"},
    ).status_code == 404

    db = next(app.dependency_overrides[get_db]())
    try:
        member = db.query(User).filter_by(email="support-target@example.com").one()
        manager_token = create_access_token(str(member.id), member.token_version)
    finally:
        db.close()
    manager_headers = {"Authorization": f"Bearer {manager_token}"}
    assert client.get(f"/api/products/?store_id={context['store_id']}", headers=manager_headers).status_code == 200

    changed = client.patch(
        f"/api/stores/{context['store_id']}/members/{membership_id}",
        headers=owner_headers,
        json={"role": "store_viewer"},
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "store_viewer"
    assert client.get("/api/auth/me", headers=manager_headers).status_code == 401

    revoked = client.patch(
        f"/api/stores/{context['store_id']}/members/{membership_id}",
        headers=owner_headers,
        json={"status": "suspended"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "suspended"
    db = next(app.dependency_overrides[get_db]())
    try:
        member = db.query(User).filter_by(email="support-target@example.com").one()
        current_token = create_access_token(str(member.id), member.token_version)
        events = db.query(AuditLog).filter_by(resource_id=str(membership_id)).all()
    finally:
        db.close()
    assert client.get(f"/api/products/?store_id={context['store_id']}", headers={"Authorization": f"Bearer {current_token}"}).status_code == 404
    assert {event.action for event in events} >= {"membership.invited", "membership.role_changed", "membership.suspended"}


def test_store_staff_can_contact_support_only_for_their_store(payment_context):
    client, context = payment_context
    own_ticket = client.post(
        "/api/support/conversations",
        headers=auth_headers(context),
        json={"store_id": context["store_id"], "message": "Please help with my store"},
    )
    unrelated_ticket = client.post(
        "/api/support/conversations",
        headers=auth_headers(context),
        json={"store_id": context["other_store_id"], "message": "Cross-store request"},
    )

    assert own_ticket.status_code == 201
    assert unrelated_ticket.status_code == 404


def test_same_store_staff_can_share_support_thread_but_other_store_staff_cannot(payment_context):
    client, context = payment_context
    ticket = client.post(
        "/api/support/conversations",
        headers=auth_headers(context),
        json={"store_id": context["store_id"], "message": "Owner asks support for help"},
    )
    assert ticket.status_code == 201
    conversation_id = ticket.json()["id"]
    store_admin_headers = {"Authorization": f"Bearer {context['store_admin_token']}"}
    other_store_headers = {"Authorization": f"Bearer {context['support_token']}"}

    shared = client.get("/api/support/conversations", headers=store_admin_headers)
    assert [item["id"] for item in shared.json()] == [conversation_id]
    assert client.post(
        f"/api/support/conversations/{conversation_id}/reply",
        headers=store_admin_headers,
        json={"message": "Admin adds context"},
    ).status_code == 200
    assert client.get(
        f"/api/support/conversations/{conversation_id}", headers=other_store_headers
    ).status_code == 404
    owner_view = client.get(
        f"/api/support/conversations/{conversation_id}", headers=auth_headers(context)
    )
    assert owner_view.status_code == 200
    assert owner_view.json()["messages"][-1]["content"] == "Admin adds context"


def test_god_transfers_store_ownership_and_audits_the_change(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("GOD_USER_EMAIL", "payments@example.com")
    owner_headers = auth_headers(context)

    response = client.patch(
        f"/api/admin/stores/{context['store_id']}/owner",
        headers=owner_headers,
        json={"user_id": context["support_user_id"]},
    )

    assert response.status_code == 200
    assert response.json()["owner_id"] == context["support_user_id"]
    assert client.get(f"/api/stores/{context['store_id']}", headers=owner_headers).status_code == 401
    assert client.get(f"/api/stores/{context['store_id']}", headers={"Authorization": f"Bearer {context['support_token']}"}).status_code == 401
    db = next(app.dependency_overrides[get_db]())
    try:
        new_owner = db.get(User, context["support_user_id"])
        god = db.get(User, context["user_id"])
        new_owner_headers = {"Authorization": f"Bearer {create_access_token(str(new_owner.id), new_owner.token_version)}"}
        refreshed_god_headers = {"Authorization": f"Bearer {create_access_token(str(god.id), god.token_version)}"}
    finally:
        db.close()
    assert client.get(f"/api/stores/{context['store_id']}", headers=new_owner_headers).status_code == 200
    logs = client.get("/api/admin/audit-logs", headers=refreshed_god_headers)
    assert any(item["action"] == "store.owner_changed" for item in logs.json())


def test_store_owner_approves_store_admin_membership(payment_context):
    client, context = payment_context
    owner_headers = auth_headers(context)
    requests = client.get(f"/api/stores/{context['store_id']}/admin-requests", headers=owner_headers)
    assert requests.status_code == 200
    assert any(item["id"] == context["admin_membership_id"] for item in requests.json())

    approved = client.patch(
        f"/api/stores/{context['store_id']}/admin-requests/{context['admin_membership_id']}",
        headers=owner_headers,
        json={"status": "approved"},
    )
    assert approved.status_code == 200
    assert approved.json()["user_approval_status"] == "active"

    db = next(app.dependency_overrides[get_db]())
    try:
        applicant = db.get(User, context["admin_applicant_id"])
        headers = {"Authorization": f"Bearer {create_access_token(str(applicant.id), applicant.token_version)}"}
    finally:
        db.close()
    stores = client.get("/api/stores/", headers=headers)
    assert [item["id"] for item in stores.json()] == [context["store_id"]]


def test_unconfigured_users_cannot_access_admin_routes(payment_context):
    client, context = payment_context
    response = client.get("/api/admin/users", headers=auth_headers(context))
    assert response.status_code == 403


def test_role_workspace_routes_serve_the_frontend_application(payment_context, monkeypatch, tmp_path):
    client, _context = payment_context
    from app import main

    frontend_dist = tmp_path / "dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<!doctype html><div id=\"root\"></div>", encoding="utf-8")
    monkeypatch.setattr(main, "frontend_dist", frontend_dist)
    for path in (
        "/workspace",
        "/workspace/customer",
        "/workspace/support",
        "/workspace/god",
        "/seller/team",
        "/seller/support",
        "/seller/platform",
        "/seller/customer",
        "/seller/contact-support",
        "/api-docs",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert 'id="root"' in response.text
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert "/api/payments/orders/{order_id}" in openapi.json()["paths"]


def test_mock_payment_is_idempotent_and_server_verified(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    headers = {**auth_headers(context), "Idempotency-Key": "payment-mock-1"}

    created = client.post(f"/payments/orders/{order['id']}", headers=headers)
    assert created.status_code == 201
    payment = created.json()
    assert payment["status"] == "pending"
    assert payment["authority"].startswith("mock-")

    repeated = client.post(f"/payments/orders/{order['id']}", headers=headers)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == payment["id"]
    alternate_key = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-mock-alternate"},
    )
    assert alternate_key.status_code == 201
    assert alternate_key.json()["id"] == payment["id"]

    verified = client.post(
        f"/payments/{payment['id']}/verify",
        headers=auth_headers(context),
        json={"authority": payment["authority"]},
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "paid"
    assert verified.json()["transaction_id"].startswith("mock-tx-")
    first_transaction_id = verified.json()["transaction_id"]
    repeated_verification = client.post(
        f"/payments/{payment['id']}/verify",
        headers=auth_headers(context),
        json={"authority": payment["authority"]},
    )
    assert repeated_verification.status_code == 200
    assert repeated_verification.json()["transaction_id"] == first_transaction_id
    finalized = client.get(f"/orders/{order['id']}", headers=auth_headers(context))
    assert finalized.status_code == 200
    assert finalized.json()["tracking_number"]
    assert finalized.json()["invoice_number"]
    seller_orders = client.get(
        f"/seller/orders/stores/{context['store_id']}",
        headers=auth_headers(context),
    )
    assert seller_orders.status_code == 200
    assert len(seller_orders.json()) == 1
    assert seller_orders.json()[0]["tracking_number"]
    assert seller_orders.json()[0]["invoice_number"]
    invoice = client.get(f"/orders/{order['id']}/invoice", headers=auth_headers(context))
    assert invoice.status_code == 200
    assert invoice.headers["content-type"] == "application/pdf"
    for locale in ("fa", "en", "es", "de", "fr"):
        localized_invoice = client.get(
            f"/orders/{order['id']}/invoice?locale={locale}&timezone=Europe%2FBerlin",
            headers=auth_headers(context),
        )
        assert localized_invoice.status_code == 200
        assert localized_invoice.content.startswith(b"%PDF")
        assert localized_invoice.headers["content-disposition"].endswith(f"-{locale}.pdf\"")
    invalid_locale = client.get(
        f"/orders/{order['id']}/invoice?locale=it",
        headers=auth_headers(context),
    )
    assert invalid_locale.status_code == 400

    db = next(app.dependency_overrides[get_db]())
    try:
        product = db.get(Product, context["product_id"])
        assert product.reserved_stock == 0
        assert product.stock == 1
    finally:
        db.close()

    invalid = client.post(
        f"/payments/{payment['id']}/verify",
        headers=auth_headers(context),
        json={"authority": "mock-invalid"},
    )
    assert invalid.status_code == 400


def test_gateway_callback_verifies_payment_on_server(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "gateway-callback-1"},
    )
    assert created.status_code == 201

    callback = client.get(
        "/api/payments/callback",
        params={"Authority": created.json()["authority"], "Status": "OK"},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert "payment=success" in callback.headers["location"]
    duplicate_callback = client.get(
        "/api/payments/callback",
        params={"Authority": created.json()["authority"], "Status": "OK"},
        follow_redirects=False,
    )
    assert duplicate_callback.status_code == 303
    assert "payment=success" in duplicate_callback.headers["location"]
    finalized = client.get(f"/orders/{order['id']}", headers=auth_headers(context))
    assert finalized.status_code == 200
    assert finalized.json()["tracking_number"]
    db = next(app.dependency_overrides[get_db]())
    try:
        product = db.get(Product, context["product_id"])
        assert product.stock == 1
        assert product.reserved_stock == 0
    finally:
        db.close()


def test_failed_gateway_verification_never_finalizes_or_deducts_stock(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-failed-verify"},
    )
    payment = created.json()

    def fail_verification(self, *, amount, currency, authority):
        raise ValueError("Payment verification failed")

    monkeypatch.setattr(MockPaymentProvider, "verify_payment", fail_verification)
    response = client.post(
        f"/payments/{payment['id']}/verify",
        headers=auth_headers(context),
        json={"authority": payment["authority"]},
    )
    assert response.status_code == 400
    assert client.get(f"/orders/{order['id']}", headers=auth_headers(context)).status_code == 404
    assert client.get(f"/orders/{order['id']}/invoice", headers=auth_headers(context)).status_code == 404
    assert client.get("/orders/track/1234567890").status_code == 404
    db = next(app.dependency_overrides[get_db]())
    try:
        stored_order = db.get(Order, order["id"])
        stored_payment = db.get(Payment, payment["id"])
        product = db.get(Product, context["product_id"])
        assert stored_order.status == "pending"
        assert stored_order.tracking_number is None
        assert stored_order.invoice_number is None
        assert stored_payment.status == "failed"
        assert product.stock == 2
        assert product.reserved_stock == 1
    finally:
        db.close()


@pytest.mark.parametrize(
    "gateway_status",
    ["Cancelled", "Expired", "Failed"],
)
def test_unverified_gateway_outcomes_cannot_finalize_or_duplicate_payment(
    payment_context,
    monkeypatch,
    gateway_status,
):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-cancelled"},
    )
    payment = created.json()
    callback = client.get(
        "/api/payments/callback",
        params={"Authority": payment["authority"], "Status": gateway_status},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert "payment=failed" in callback.headers["location"]
    assert client.get(f"/orders/{order['id']}", headers=auth_headers(context)).status_code == 404
    retry = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-retry-after-nok"},
    )
    assert retry.status_code == 201
    assert retry.json()["id"] == payment["id"]
    db = next(app.dependency_overrides[get_db]())
    try:
        stored_order = db.get(Order, order["id"])
        stored_payment = db.get(Payment, payment["id"])
        assert stored_order.tracking_number is None
        assert stored_order.invoice_number is None
        assert stored_payment.status == "pending"
    finally:
        db.close()


def test_unverified_failure_callback_does_not_block_later_verified_success(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    payment = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-fake-nok"},
    ).json()

    failed_callback = client.get(
        "/api/payments/callback",
        params={"Authority": payment["authority"], "Status": "NOK"},
        follow_redirects=False,
    )
    success_callback = client.get(
        "/api/payments/callback",
        params={"Authority": payment["authority"], "Status": "OK"},
        follow_redirects=False,
    )

    assert "payment=failed" in failed_callback.headers["location"]
    assert "payment=success" in success_callback.headers["location"]
    assert client.get(f"/orders/{order['id']}", headers=auth_headers(context)).json()["tracking_number"]


def test_pending_payment_blocks_order_cancellation(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    payment = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-before-cancel"},
    ).json()

    response = client.post(f"/orders/{order['id']}/cancel", headers=auth_headers(context))

    assert response.status_code == 400
    assert "Pending payments" in response.json()["detail"]
    assert client.get(f"/orders/{order['id']}", headers=auth_headers(context)).status_code == 404
    db = next(app.dependency_overrides[get_db]())
    try:
        stored_order = db.get(Order, order["id"])
        stored_payment = db.get(Payment, payment["id"])
        product = db.get(Product, context["product_id"])
        assert stored_order.status == "pending"
        assert stored_payment.status == "pending"
        assert product.stock == 2
        assert product.reserved_stock == 1
    finally:
        db.close()


def test_invalid_gateway_callback_does_not_change_payment_or_order(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-invalid-callback"},
    )
    callback = client.get(
        "/api/payments/callback",
        params={"Authority": "not-a-real-authority", "Status": "OK"},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert "payment=failed" in callback.headers["location"]
    assert client.get(f"/orders/{order['id']}", headers=auth_headers(context)).status_code == 404
    db = next(app.dependency_overrides[get_db]())
    try:
        assert db.get(Payment, created.json()["id"]).status == "pending"
    finally:
        db.close()


def test_missing_reserved_stock_prevents_finalization(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-stock-conflict"},
    )
    payment = created.json()
    db = next(app.dependency_overrides[get_db]())
    try:
        product = db.get(Product, context["product_id"])
        product.reserved_stock = 0
        db.commit()
    finally:
        db.close()
    response = client.post(
        f"/payments/{payment['id']}/verify",
        headers=auth_headers(context),
        json={"authority": payment["authority"]},
    )
    assert response.status_code == 400
    assert client.get(f"/orders/{order['id']}", headers=auth_headers(context)).status_code == 404