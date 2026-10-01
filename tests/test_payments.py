from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.database import Base, get_db
from app.db.models import AuditLog, FAQ, KnowledgeBaseEntry, Order, Payment, Product, Store, StoreMembership, User
from app.main import app
from app.services.payment_service import PaymentProviderNotConfigured, get_payment_provider
from app.services.payment_service import MockPaymentProvider
from app.services.audit_service import content_audit_state


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


def test_payment_requires_configured_provider(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.delenv("PAYMENT_PROVIDER", raising=False)
    order = create_order(client, context)

    response = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-disabled-1"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Payment provider is not configured"


def test_production_rejects_mock_payment_provider(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")

    with pytest.raises(PaymentProviderNotConfigured):
        get_payment_provider()


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

    def fail_verification(self, *, amount, authority):
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
    ("gateway_status", "expected_payment_status"),
    [("Cancelled", "cancelled"), ("Expired", "expired"), ("Failed", "failed")],
)
def test_unsuccessful_gateway_outcomes_cannot_finalize_or_be_verified_later(
    payment_context,
    monkeypatch,
    gateway_status,
    expected_payment_status,
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
    assert client.post(
        f"/payments/{payment['id']}/verify",
        headers=auth_headers(context),
        json={"authority": payment["authority"]},
    ).status_code == 400
    assert client.get(f"/orders/{order['id']}", headers=auth_headers(context)).status_code == 404
    db = next(app.dependency_overrides[get_db]())
    try:
        stored_order = db.get(Order, order["id"])
        stored_payment = db.get(Payment, payment["id"])
        assert stored_order.tracking_number is None
        assert stored_order.invoice_number is None
        assert stored_payment.status == expected_payment_status
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