from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Order, Store, StoreMembership, User
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
        user = db.get(User, seller_id)
        filters = [Store.id == store_id]
        if user is not None and user.role == "god":
            pass
        elif user is not None and user.role == "store_admin":
            filters.append(
                Store.id.in_(
                    select(StoreMembership.store_id).where(
                        StoreMembership.user_id == seller_id,
                        StoreMembership.status == "approved",
                    )
                )
            )
        else:
            filters.append(Store.owner_id == seller_id)
        store = db.scalar(select(Store).where(*filters))

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
    ) -> Order:
        user = db.get(User, seller_id)
        filters = [Order.id == order_id]
        if user is not None and user.role == "god":
            pass
        elif user is not None and user.role == "store_admin":
            filters.append(
                Store.id.in_(
                    select(StoreMembership.store_id).where(
                        StoreMembership.user_id == seller_id,
                        StoreMembership.status == "approved",
                    )
                )
            )
        else:
            filters.append(Store.owner_id == seller_id)
        order = db.scalar(
            select(Order)
            .join(Store, Order.store_id == Store.id)
            .options(joinedload(Order.items))
            .where(
                *filters,
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