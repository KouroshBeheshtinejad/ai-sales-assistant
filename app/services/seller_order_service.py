from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Order, Store, User
from app.security.policies import store_scope_filter
from app.services.order_service import OrderService
from app.services.audit_service import record_audit_log


class SellerOrderService:
    VALID_STATUSES = {
        "pending",
        "confirmed",
        "preparing",
        "shipped",
        "delivered",
        "cancelled",
    }

    STATUS_TRANSITIONS = {
        "pending": {"confirmed", "cancelled"},
        "confirmed": {"preparing", "cancelled"},
        "preparing": {"shipped"},
        "shipped": {"delivered"},
        "delivered": set(),
        "cancelled": set(),
    }

    @staticmethod
    def _get_owned_store(
        db: Session,
        seller_id: int,
        store_id: int,
    ) -> Store:
        user = db.get(User, seller_id)
        store = None if user is None else db.scalar(
            select(Store).where(
                Store.id == store_id,
                store_scope_filter(user, "order.read"),
            )
        )

        if store is None:
            raise ValueError("Store not found")

        return store

    @staticmethod
    def list_store_orders(
        db: Session,
        seller_id: int,
        store_id: int,
    ) -> list[Order]:
        SellerOrderService._get_owned_store(
            db=db,
            seller_id=seller_id,
            store_id=store_id,
        )

        orders = db.scalars(
            select(Order)
            .options(joinedload(Order.items))
            .where(Order.store_id == store_id, OrderService.finalized_order_filter())
            .order_by(Order.created_at.desc())
        ).unique().all()

        return list(orders)

    @staticmethod
    def get_order(
        db: Session,
        seller_id: int,
        order_id: int,
        permission: str = "order.read",
    ) -> Order:
        user = db.get(User, seller_id)
        order = None if user is None else db.scalar(
            select(Order)
            .join(Store, Order.store_id == Store.id)
            .options(joinedload(Order.items))
            .where(
                Order.id == order_id,
                store_scope_filter(user, permission),
                OrderService.finalized_order_filter(),
            )
        )

        if order is None:
            raise ValueError("Order not found")

        return order

    @staticmethod
    def update_status(
        db: Session,
        seller_id: int,
        order_id: int,
        new_status: str,
        actor: User | None = None,
        ip_address: str | None = None,
    ) -> Order:
        if new_status not in SellerOrderService.VALID_STATUSES:
            raise ValueError("Invalid status")

        order = SellerOrderService.get_order(
            db=db,
            seller_id=seller_id,
            order_id=order_id,
            permission="order.cancel" if new_status == "cancelled" else "order.update",
        )

        allowed_statuses = SellerOrderService.STATUS_TRANSITIONS.get(
            order.status,
            set(),
        )

        if new_status not in allowed_statuses:
            raise ValueError(
                f"Cannot change status from '{order.status}' "
                f"to '{new_status}'"
            )

        previous_status = order.status
        if new_status == "cancelled":
            OrderService.release_order_stock(db, order)
        order.status = new_status
        if actor is not None:
            record_audit_log(
                db,
                actor=actor,
                action="order.status_changed",
                resource_type="order",
                resource_id=order.id,
                store_id=order.store_id,
                before_state={"status": previous_status},
                after_state={"status": order.status},
                ip_address=ip_address,
            )

        db.commit()
        db.refresh(order)

        return order