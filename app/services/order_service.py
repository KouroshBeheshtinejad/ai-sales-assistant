from datetime import datetime, timezone
from decimal import Decimal
import secrets
import logging

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.db.models import Cart, CartItem, Conversation, Order, OrderItem, Product
from app.services.notification_service import notify_order_created


class OrderService:
    logger = logging.getLogger(__name__)

    @staticmethod
    def release_order_stock(db: Session, order: Order) -> None:
        """Release an unpaid order's reservation exactly once."""
        if any(payment.status == "paid" for payment in order.payments):
            raise ValueError("Paid orders require a refund before cancellation")
        for item in order.items:
            if item.product_id is None:
                continue
            product = db.get(Product, item.product_id)
            if product is not None:
                product.reserved_stock -= item.quantity

    @staticmethod
    def _new_tracking_number(db: Session) -> str:
        for _ in range(10):
            tracking_number = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
            if db.scalar(select(Order.id).where(Order.tracking_number == tracking_number)) is None:
                return tracking_number
        raise ValueError("Could not allocate a unique tracking number")

    @staticmethod
    def create_order(
        db: Session,
        user_id: int | None,
        store_id: int,
        customer_name: str,
        customer_phone: str,
        customer_address: str,
        customer_first_name: str | None = None,
        customer_last_name: str | None = None,
        customer_email: str | None = None,
        guest_token: str | None = None,
        idempotency_key: str | None = None,
    ) -> Order:
        """
        تبدیل سبد خرید کاربر به سفارش.
        """

        if user_id is None and not guest_token:
            raise ValueError("A user or guest token is required")

        if guest_token:
            conversation = db.scalar(
                select(Conversation).where(
                    Conversation.guest_token == guest_token,
                    Conversation.store_id == store_id,
                )
            )
            if conversation is None:
                raise ValueError("Guest token is not valid for this store")
            assert conversation is not None

        if idempotency_key:
            existing_order = db.scalar(
                select(Order).where(
                    Order.store_id == store_id,
                    Order.idempotency_key == idempotency_key,
                    (
                        Order.user_id == user_id
                        if user_id is not None
                        else Order.guest_token == guest_token
                    ),
                )
            )
            if existing_order is not None:
                return existing_order

        if guest_token:
            assert conversation is not None

        identity_filters = [Cart.store_id == store_id]
        if user_id is not None:
            identity_filters.append(Cart.user_id == user_id)
        else:
            identity_filters.append(Cart.guest_token == guest_token)

        cart = db.scalar(
            select(Cart)
            .options(
                joinedload(Cart.items).joinedload(CartItem.product)
            )
            .where(*identity_filters)
        )

        if cart is None or not cart.items:
            raise ValueError("Cart is empty")

        total_amount = Decimal("0.00")
        order_items = []

        # بررسی محصولات و موجودی قبل از ایجاد سفارش
        for cart_item in sorted(cart.items, key=lambda item: item.product_id):
            product = db.scalar(
                select(Product)
                .where(Product.id == cart_item.product_id)
                .with_for_update()
            )

            if product is None:
                raise ValueError("Product no longer exists")

            if product.store_id != store_id:
                raise ValueError("Product does not belong to this store")

            if not product.is_active:
                raise ValueError(
                    f"Product '{product.name}' is inactive"
                )

            if product.stock - product.reserved_stock < cart_item.quantity:
                raise ValueError(
                    f"Insufficient stock for product '{product.name}'"
                )

            unit_price = Decimal(str(product.price))
            line_total = unit_price * cart_item.quantity

            total_amount += line_total

            order_items.append(
                OrderItem(
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=unit_price,
                    quantity=cart_item.quantity,
                    line_total=line_total,
                )
            )

        # ایجاد سفارش
        order = Order(
            tracking_number=OrderService._new_tracking_number(db),
            user_id=user_id,
            guest_token=guest_token,
            store_id=store_id,
            status="pending",
            customer_name=customer_name,
            customer_first_name=customer_first_name,
            customer_last_name=customer_last_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            customer_address=customer_address,
            total_amount=total_amount,
            idempotency_key=idempotency_key,
        )

        db.add(order)
        db.flush()
        order.invoice_number = f"INV-{datetime.now(timezone.utc):%Y%m%d}-{order.id:06d}"

        if guest_token:
            assert conversation is not None
            conversation.last_order_id = order.id
            conversation.checkout_state = "completed"

        # کاهش موجودی و اتصال اقلام به سفارش
        for cart_item, order_item in zip(
            sorted(cart.items, key=lambda item: item.product_id), order_items
        ):
            result = db.execute(
                update(Product)
                .where(
                    Product.id == cart_item.product_id,
                    Product.stock - Product.reserved_stock >= cart_item.quantity,
                )
                .values(
                    reserved_stock=Product.reserved_stock + cart_item.quantity,
                )
            )
            if getattr(result, "rowcount", 0) != 1:
                raise ValueError(
                    f"Insufficient stock for product '{order_item.product_name}'"
                )
            order.items.append(order_item)

        # حذف اقلام سبد خرید
        for cart_item in list(cart.items):
            db.delete(cart_item)

        db.commit()
        db.refresh(order)
        OrderService.logger.info("order_created order_id=%s store_id=%s", order.id, store_id)
        notify_order_created(order)

        return order

    @staticmethod
    def get_order_by_id(
        db: Session,
        order_id: int,
        user_id: int,
    ) -> Order | None:
        """
        دریافت یک سفارش متعلق به کاربر.
        """

        return db.scalar(
            select(Order)
            .options(joinedload(Order.items))
            .where(
                Order.id == order_id,
                Order.user_id == user_id,
            )
        )

    @staticmethod
    def get_order_by_tracking_number(
        db: Session,
        tracking_number: str,
    ) -> Order | None:
        if len(tracking_number) != 10 or not tracking_number.isdigit():
            return None
        return db.scalar(
            select(Order)
            .options(joinedload(Order.store))
            .where(Order.tracking_number == tracking_number)
        )

    @staticmethod
    def get_guest_order(
        db: Session,
        order_id: int,
        store_id: int,
        guest_token: str,
    ) -> Order | None:
        return db.scalar(
            select(Order)
            .options(joinedload(Order.items))
            .where(
                Order.id == order_id,
                Order.store_id == store_id,
                Order.user_id.is_(None),
                Order.guest_token == guest_token,
            )
        )

    @staticmethod
    def list_user_orders(
        db: Session,
        user_id: int,
    ) -> list[Order]:
        """
        دریافت تمام سفارش‌های کاربر.
        """

        return list(
            db.scalars(
                select(Order)
                .options(joinedload(Order.items))
                .where(Order.user_id == user_id)
                .order_by(Order.created_at.desc())
            ).unique()
        )

    @staticmethod
    def cancel_order(
        db: Session,
        order_id: int,
        user_id: int,
    ) -> Order:
        """
        لغو سفارش در وضعیت pending.
        """

        order = db.scalar(
            select(Order)
            .options(joinedload(Order.items))
            .where(
                Order.id == order_id,
                Order.user_id == user_id,
            )
        )

        if order is None:
            raise ValueError("Order not found")

        if order.status != "pending":
            raise ValueError(
                "Only pending orders can be cancelled"
            )

        order.status = "cancelled"
        order.cancelled_at = datetime.now(timezone.utc)

        OrderService.release_order_stock(db, order)

        db.commit()
        db.refresh(order)

        return order