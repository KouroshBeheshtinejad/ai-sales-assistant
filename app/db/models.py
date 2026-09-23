from datetime import datetime, timezone
from decimal import Decimal
import secrets

import json

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.type_api import UserDefinedType
from sqlalchemy.types import TypeDecorator

from app.db.database import Base
from app.services.embedding_provider import DEFAULT_EMBEDDING_DIMENSION


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _tracking_number() -> str:
    return str(secrets.randbelow(9_000_000_000) + 1_000_000_000)

def _invoice_number() -> str:
    return f"INV-{datetime.now(timezone.utc):%Y%m%d}-{secrets.randbelow(1_000_000):06d}"


class _PostgresVector(UserDefinedType):
    cache_ok = True

    def __init__(self, dimensions: int):
        self.dimensions = dimensions

    def get_col_spec(self, **kw):
        return f"vector({self.dimensions})"


class EmbeddingVector(TypeDecorator):
    """Use pgvector in PostgreSQL and JSON for isolated SQLite test databases."""

    impl = JSON
    cache_ok = True

    def __init__(self, dimensions: int):
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PostgresVector(self.dimensions))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return "[" + ",".join(f"{float(item):.10g}" for item in value) + "]"
        return list(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, list):
            return value
        if dialect.name == "postgresql" and isinstance(value, str):
            return [float(item) for item in json.loads(value)]
        return value


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
    )

    stores: Mapped[list["Store"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    
    carts: Mapped[list["Cart"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    business_type: Mapped[str] = mapped_column(
        String(100),
        default="clothing",
        index=True,
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
    )

    owner: Mapped["User"] = relationship(
        back_populates="stores",
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
    )

    faqs: Mapped[list["FAQ"]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
    )

    knowledge_entries: Mapped[list["KnowledgeBaseEntry"]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
    )
    
    carts: Mapped[list["Cart"]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="store",
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
    )


class FAQ(Base):
    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
    )

    store: Mapped["Store"] = relationship(
        back_populates="faqs",
    )


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
    )

    store: Mapped["Store"] = relationship(
        back_populates="knowledge_entries",
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("stock >= 0", name="ck_products_stock_nonnegative"),
        CheckConstraint(
            "reserved_stock >= 0",
            name="ck_products_reserved_stock_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255), index=True)

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    price: Mapped[float] = mapped_column(Numeric(12, 2))

    stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    reserved_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    size: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    color: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    attributes: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id"),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
    )

    store: Mapped["Store"] = relationship(
        back_populates="products",
    )


class SemanticDocument(Base):
    """A non-authoritative vector index entry for one searchable store record."""

    __tablename__ = "semantic_documents"
    __table_args__ = (
        UniqueConstraint("store_id", "source_type", "source_id", name="uq_semantic_document_source"),
        Index("ix_semantic_documents_store_active", "store_id", "is_active"),
        Index("ix_semantic_documents_source", "source_type", "source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        EmbeddingVector(DEFAULT_EMBEDDING_DIMENSION),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_store_status", "store_id", "status"),
        CheckConstraint(
            "(user_id IS NOT NULL) OR (guest_token IS NOT NULL)",
            name="ck_conversations_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    guest_token: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    checkout_state: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="idle",
    )

    checkout_customer_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    checkout_customer_phone: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )
    checkout_customer_address: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    checkout_idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True,
    )
    last_order_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )

    store: Mapped["Store"] = relationship(
        back_populates="conversations",
    )

    user: Mapped["User | None"] = relationship(
        back_populates="conversations",
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages",
    )


class Cart(Base):
    __tablename__ = "carts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "store_id",
            name="uq_cart_user_store",
        ),
        UniqueConstraint(
            "guest_token",
            "store_id",
            name="uq_cart_guest_store",
        ),
        CheckConstraint(
            "(user_id IS NOT NULL) OR (guest_token IS NOT NULL)",
            name="ck_carts_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    guest_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
    )

    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="carts",
    )

    store: Mapped["Store"] = relationship(
        back_populates="carts",
    )

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan",
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint(
            "cart_id",
            "product_id",
            name="uq_cart_item_product",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        nullable=False,
    )

    cart: Mapped["Cart"] = relationship(
        back_populates="items",
    )

    product: Mapped["Product"] = relationship()


class Order(Base):
    __tablename__ = "orders"

    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "user_id",
            "guest_token",
            "idempotency_key",
            name="uq_orders_scoped_idempotency",
        ),
        CheckConstraint(
            "(user_id IS NOT NULL) OR (guest_token IS NOT NULL)",
            name="ck_orders_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    tracking_number: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        index=True,
        nullable=False,
        default=_tracking_number,
    )
    invoice_number: Mapped[str] = mapped_column(
        String(40), unique=True, index=True, nullable=False, default=_invoice_number,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    guest_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True,
    )

    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )

    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    customer_first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    customer_last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    customer_phone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    customer_address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    user: Mapped["User"] = relationship()

    store: Mapped["Store"] = relationship(
        back_populates="orders",
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    order: Mapped["Order"] = relationship(
        back_populates="items",
    )

    product: Mapped["Product | None"] = relationship()


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    __table_args__ = (
        Index("ix_verification_codes_user_channel", "user_id", "channel"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    user: Mapped["User"] = relationship()


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    user: Mapped["User"] = relationship()


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("order_id", "idempotency_key", name="uq_payment_order_idempotency"),
        UniqueConstraint("authority", name="uq_payments_authority"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    authority: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payment_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="payments")
