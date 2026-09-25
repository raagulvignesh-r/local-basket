import enum
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class FulfillmentType(str, enum.Enum):
    click_and_collect = "click_and_collect"
    home_delivery = "home_delivery"


class OrderStatus(str, enum.Enum):
    created = "created"
    inventory_reserved = "inventory_reserved"
    payment_confirmed = "payment_confirmed"
    confirmed = "confirmed"
    picking = "picking"
    packed = "packed"
    ready_for_pickup = "ready_for_pickup"
    collected = "collected"
    delivery_assigned = "delivery_assigned"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.created: {OrderStatus.inventory_reserved, OrderStatus.cancelled},
    OrderStatus.inventory_reserved: {
        OrderStatus.payment_confirmed,
        OrderStatus.cancelled,
    },
    OrderStatus.payment_confirmed: {OrderStatus.confirmed},
    OrderStatus.confirmed: {OrderStatus.picking},
    OrderStatus.picking: {OrderStatus.packed},
    OrderStatus.packed: {
        OrderStatus.ready_for_pickup,
        OrderStatus.delivery_assigned,
    },
    OrderStatus.ready_for_pickup: {OrderStatus.collected},
    OrderStatus.delivery_assigned: {OrderStatus.out_for_delivery},
    OrderStatus.out_for_delivery: {OrderStatus.delivered},
}


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id"), nullable=False
    )
    fulfillment_type: Mapped[FulfillmentType] = mapped_column(
        Enum(FulfillmentType), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.created, nullable=False
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id"), nullable=False
    )
    store_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("store_products.id"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")


def transition(order: Order, new_status: OrderStatus) -> None:
    if new_status not in ALLOWED_TRANSITIONS.get(order.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot move from {order.status.value} to {new_status.value}",
        )

    if new_status in {OrderStatus.ready_for_pickup, OrderStatus.collected}:
        if order.fulfillment_type != FulfillmentType.click_and_collect:
            raise HTTPException(
                status_code=409,
                detail="Pickup statuses require click and collect fulfillment",
            )

    if new_status in {
        OrderStatus.delivery_assigned,
        OrderStatus.out_for_delivery,
        OrderStatus.delivered,
    }:
        if order.fulfillment_type != FulfillmentType.home_delivery:
            raise HTTPException(
                status_code=409,
                detail="Delivery statuses require home delivery fulfillment",
            )

    order.status = new_status
