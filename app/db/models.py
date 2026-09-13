from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, Numeric, Integer, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    stores: Mapped[list["Store"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        default=datetime.utcnow,
    )

    owner: Mapped["User"] = relationship(
        back_populates="stores",
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255), index=True)

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    price: Mapped[float] = mapped_column(Numeric(12, 2))

    stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

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
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    store: Mapped["Store"] = relationship(
        back_populates="products",
    )