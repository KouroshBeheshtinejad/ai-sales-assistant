from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Cart, CartItem, Product


class CartService:
    @staticmethod
    def get_or_create_cart(
        db: Session,
        user_id: int,
        store_id: int,
    ) -> Cart:
        """دریافت سبد خرید کاربر برای یک فروشگاه یا ساخت آن."""

        stmt = (
            select(Cart)
            .where(
                Cart.user_id == user_id,
                Cart.store_id == store_id,
            )
            .options(
                joinedload(Cart.items).joinedload(CartItem.product)
            )
        )

        cart = db.execute(stmt).unique().scalar_one_or_none()

        if cart is None:
            cart = Cart(
                user_id=user_id,
                store_id=store_id,
            )
            db.add(cart)
            db.commit()
            db.refresh(cart)

        return cart

    @staticmethod
    def add_item(
        db: Session,
        user_id: int,
        store_id: int,
        product_id: int,
        quantity: int,
    ) -> Cart:
        """افزودن محصول به سبد خرید."""

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        product = db.get(Product, product_id)

        if product is None:
            raise ValueError("Product not found.")

        if product.store_id != store_id:
            raise ValueError("Product does not belong to this store.")

        if not product.is_active:
            raise ValueError("Product is not active.")

        if product.stock < quantity:
            raise ValueError("Insufficient stock.")

        cart = CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
        )

        item = next(
            (
                item
                for item in cart.items
                if item.product_id == product_id
            ),
            None,
        )

        if item is None:
            item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity,
            )
            db.add(item)
        else:
            new_quantity = item.quantity + quantity

            if new_quantity > product.stock:
                raise ValueError("Insufficient stock.")

            item.quantity = new_quantity

        db.commit()
        db.refresh(cart)

        return CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
        )

    @staticmethod
    def update_item(
        db: Session,
        user_id: int,
        store_id: int,
        product_id: int,
        quantity: int,
    ) -> Cart:
        """تغییر تعداد یک محصول در سبد خرید."""

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        cart = CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
        )

        item = next(
            (
                item
                for item in cart.items
                if item.product_id == product_id
            ),
            None,
        )

        if item is None:
            raise ValueError("Cart item not found.")

        product = db.get(Product, product_id)

        if product is None:
            raise ValueError("Product not found.")

        if product.stock < quantity:
            raise ValueError("Insufficient stock.")

        item.quantity = quantity

        db.commit()
        db.refresh(cart)

        return CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
        )

    @staticmethod
    def remove_item(
        db: Session,
        user_id: int,
        store_id: int,
        product_id: int,
    ) -> Cart:
        """حذف یک محصول از سبد خرید."""

        cart = CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
        )

        item = next(
            (
                item
                for item in cart.items
                if item.product_id == product_id
            ),
            None,
        )

        if item is None:
            raise ValueError("Cart item not found.")

        db.delete(item)
        db.commit()

        return CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
        )

    @staticmethod
    def clear_cart(
        db: Session,
        user_id: int,
        store_id: int,
    ) -> None:
        """خالی‌کردن کامل سبد خرید."""

        cart = CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
        )

        cart.items.clear()
        db.commit()

    @staticmethod
    def calculate_total(cart: Cart) -> Decimal:
        """محاسبه مجموع قیمت محصولات سبد خرید."""

        total = Decimal("0.00")

        for item in cart.items:
            if item.product is not None:
                total += (
                    Decimal(str(item.product.price))
                    * item.quantity
                )

        return total