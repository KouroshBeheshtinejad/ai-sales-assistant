from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Cart, CartItem, Conversation, Product


MAX_CART_QUANTITY = 100


class CartService:
    @staticmethod
    def _validate_guest_store(
        db: Session,
        guest_token: str | None,
        store_id: int,
    ) -> None:
        if guest_token is None:
            return
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.guest_token == guest_token,
                Conversation.store_id == store_id,
            )
            .first()
        )
        if conversation is None:
            raise ValueError("Guest token is not valid for this store.")

    @staticmethod
    def get_or_create_cart(
        db: Session,
        user_id: int | None,
        store_id: int,
        guest_token: str | None = None,
    ) -> Cart:
        """دریافت سبد خرید کاربر برای یک فروشگاه یا ساخت آن."""

        if user_id is None and not guest_token:
            raise ValueError("A user or guest token is required.")
        CartService._validate_guest_store(db, guest_token, store_id)

        identity_filter = (
            Cart.user_id == user_id
            if user_id is not None
            else Cart.guest_token == guest_token
        )
        stmt = (
            select(Cart)
            .where(identity_filter, Cart.store_id == store_id)
            .options(
                joinedload(Cart.items).joinedload(CartItem.product)
            )
        )

        cart = db.execute(stmt).unique().scalar_one_or_none()

        if cart is None:
            cart = Cart(
                user_id=user_id,
                store_id=store_id,
                guest_token=guest_token,
            )
            db.add(cart)
            db.commit()
            db.refresh(cart)

        return cart

    @staticmethod
    def add_item(
        db: Session,
        user_id: int | None,
        store_id: int,
        product_id: int,
        quantity: int,
        guest_token: str | None = None,
    ) -> Cart:
        """افزودن محصول به سبد خرید."""

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if quantity > MAX_CART_QUANTITY:
            raise ValueError(f"Quantity cannot exceed {MAX_CART_QUANTITY}.")

        product = db.get(Product, product_id)

        if product is None:
            raise ValueError("Product not found.")

        if product.store_id != store_id:
            raise ValueError("Product does not belong to this store.")

        if not product.is_active:
            raise ValueError("Product is not active.")

        if product.stock - product.reserved_stock < quantity:
            raise ValueError("Insufficient stock.")

        cart = CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
            guest_token=guest_token,
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

            if new_quantity > MAX_CART_QUANTITY:
                raise ValueError(
                    f"Quantity must be between 1 and {MAX_CART_QUANTITY}."
                )
            if new_quantity > product.stock - product.reserved_stock:
                raise ValueError("Insufficient stock.")

            item.quantity = new_quantity

        db.commit()
        db.refresh(cart)

        return CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
            guest_token=guest_token,
        )

    @staticmethod
    def update_item(
        db: Session,
        user_id: int | None,
        store_id: int,
        product_id: int,
        quantity: int,
        guest_token: str | None = None,
    ) -> Cart:
        """تغییر تعداد یک محصول در سبد خرید."""

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if quantity > MAX_CART_QUANTITY:
            raise ValueError(f"Quantity cannot exceed {MAX_CART_QUANTITY}.")

        cart = CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
            guest_token=guest_token,
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

        if product.store_id != store_id or not product.is_active:
            raise ValueError("Product is not available in this store.")

        if product.stock - product.reserved_stock < quantity:
            raise ValueError("Insufficient stock.")

        item.quantity = quantity

        db.commit()
        db.refresh(cart)

        return CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
            guest_token=guest_token,
        )

    @staticmethod
    def remove_item(
        db: Session,
        user_id: int | None,
        store_id: int,
        product_id: int,
        guest_token: str | None = None,
    ) -> Cart:
        """حذف یک محصول از سبد خرید."""

        cart = CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
            guest_token=guest_token,
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
            guest_token=guest_token,
        )

    @staticmethod
    def clear_cart(
        db: Session,
        user_id: int | None,
        store_id: int,
        guest_token: str | None = None,
    ) -> None:
        """خالی‌کردن کامل سبد خرید."""

        cart = CartService.get_or_create_cart(
            db=db,
            user_id=user_id,
            store_id=store_id,
            guest_token=guest_token,
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