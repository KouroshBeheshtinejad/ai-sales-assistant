from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Order, Store
from app.services.order_service import OrderService


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
        store = db.scalar(
            select(Store).where(
                Store.id == store_id,
                Store.owner_id == seller_id,
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
            .where(Order.store_id == store_id)
            .order_by(Order.created_at.desc())
        ).unique().all()

        return list(orders)

    @staticmethod
    def get_order(
        db: Session,
        seller_id: int,
        order_id: int,
    ) -> Order:
        order = db.scalar(
            select(Order)
            .join(Store, Order.store_id == Store.id)
            .options(joinedload(Order.items))
            .where(
                Order.id == order_id,
                Store.owner_id == seller_id,
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
    ) -> Order:
        if new_status not in SellerOrderService.VALID_STATUSES:
            raise ValueError("Invalid status")

        order = SellerOrderService.get_order(
            db=db,
            seller_id=seller_id,
            order_id=order_id,
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

        if new_status == "cancelled":
            OrderService.release_order_stock(db, order)
        order.status = new_status

        db.commit()
        db.refresh(order)

        return order