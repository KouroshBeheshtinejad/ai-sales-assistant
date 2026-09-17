from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Cart, CartItem, Order, OrderItem, Product


class OrderService:

    @staticmethod
    def create_order(
        db: Session,
        user_id: int,
        store_id: int,
        customer_name: str,
        customer_phone: str,
        customer_address: str,
    ) -> Order:
        """
        تبدیل سبد خرید کاربر به سفارش.
        """

        cart = db.scalar(
            select(Cart)
            .options(
                joinedload(Cart.items).joinedload(CartItem.product)
            )
            .where(
                Cart.user_id == user_id,
                Cart.store_id == store_id,
            )
        )

        if cart is None or not cart.items:
            raise ValueError("Cart is empty")

        total_amount = Decimal("0.00")
        order_items = []

        # بررسی محصولات و موجودی قبل از ایجاد سفارش
        for cart_item in cart.items:
            product = cart_item.product

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
            store_id=store_id,
            status="pending",
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            total_amount=total_amount,
        )

        db.add(order)
        db.flush()

        # کاهش موجودی و اتصال اقلام به سفارش
        for cart_item, order_item in zip(cart.items, order_items):
            cart_item.product.stock -= cart_item.quantity
            order.items.append(order_item)

        # حذف اقلام سبد خرید
        for cart_item in list(cart.items):
            db.delete(cart_item)

        db.commit()
        db.refresh(order)

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