from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Cart, CartItem, Conversation, Order, OrderItem, Product
from app.services.notification_service import notify_order_created


class OrderService:

    @staticmethod
    def create_order(
        db: Session,
        user_id: int | None,
        store_id: int,
        customer_name: str,
        customer_phone: str,
        customer_address: str,
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

        if idempotency_key:
            existing_order = db.scalar(
                select(Order).where(Order.idempotency_key == idempotency_key)
            )
            if existing_order is not None:
                if existing_order.store_id != store_id or (
                    user_id is not None and existing_order.user_id != user_id
                ) or (
                    user_id is None and existing_order.guest_token != guest_token
                ):
                    raise ValueError("Invalid idempotency key")
                return existing_order

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
        for cart_item in cart.items:
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

            if product.stock < cart_item.quantity:
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
            user_id=user_id,
            guest_token=guest_token,
            store_id=store_id,
            status="pending",
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            total_amount=total_amount,
            idempotency_key=idempotency_key,
        )

        db.add(order)
        db.flush()

        if guest_token:
            conversation.last_order_id = order.id
            conversation.checkout_state = "completed"

        # کاهش موجودی و اتصال اقلام به سفارش
        for cart_item, order_item in zip(cart.items, order_items):
            cart_item.product.stock -= cart_item.quantity
            order.items.append(order_item)

        # حذف اقلام سبد خرید
        for cart_item in list(cart.items):
            db.delete(cart_item)

        db.commit()
        db.refresh(order)
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

        # بازگرداندن موجودی محصولات
        for item in order.items:
            if item.product_id is not None:
                product = db.get(Product, item.product_id)

                if product is not None:
                    product.stock += item.quantity

        db.commit()
        db.refresh(order)

        return order