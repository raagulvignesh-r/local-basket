from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.cart.models import Cart
from app.catalog.models import Product
from app.catalog.store_product_models import StoreProduct
from app.database.session import get_db
from app.inventory.models import Inventory
from app.inventory.service import reserve_quantity
from app.orders.models import (
    FulfillmentType,
    Order,
    OrderItem,
    OrderStatus,
    transition,
)
from app.orders.schemas import CheckoutRequest, OrderOut, OrderStatusUpdate
from app.stores.models import Store
from app.users.models import User, UserRole


router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "/checkout/{store_id}",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
)
def checkout(
    store_id: UUID,
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = db.get(Store, store_id)
    if store is None or not store.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    cart = db.scalar(
        select(Cart)
        .where(Cart.user_id == current_user.id, Cart.store_id == store_id)
        .options(selectinload(Cart.items))
    )
    if cart is None or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    snapshots: list[tuple[Cart, StoreProduct, Product]] = []
    total = 0
    try:
        for cart_item in cart.items:
            listing = db.get(StoreProduct, cart_item.store_product_id)
            if listing is None or listing.store_id != store_id or not listing.is_available:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Store product {cart_item.store_product_id} is unavailable",
                )

            product = db.get(Product, listing.product_id)
            if product is None or not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Product {listing.product_id} is unavailable",
                )

            inventory = db.scalar(
                select(Inventory).where(
                    Inventory.store_product_id == listing.id
                )
            )
            if inventory is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Inventory is not configured for {listing.id}",
                )

            reserved = reserve_quantity(db, listing.id, cart_item.quantity)
            if reserved is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient stock for store product {listing.id}",
                )

            total += listing.price * cart_item.quantity
            snapshots.append((cart_item, listing, product))

        order = Order(
            user_id=current_user.id,
            store_id=store_id,
            fulfillment_type=payload.fulfillment_type,
            status=OrderStatus.inventory_reserved,
            total=total,
        )
        order.items = [
            OrderItem(
                store_product_id=listing.id,
                product_name=product.name,
                unit_price=listing.price,
                quantity=cart_item.quantity,
            )
            for cart_item, listing, product in snapshots
        ]
        db.add(order)
        db.delete(cart)
        db.commit()
    except HTTPException:
        db.rollback()
        raise

    db.refresh(order)
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    is_staff_for_store = current_user.role == UserRole.admin or (
        current_user.role == UserRole.employee
        and current_user.store_id == order.store_id
    )
    if payload.status == OrderStatus.cancelled:
        is_customer_cancellation = (
            current_user.id == order.user_id
            and current_user.role == UserRole.customer
        )
        if not is_customer_cancellation and not is_staff_for_store:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot cancel this order",
            )
        if is_customer_cancellation and order.status not in {
            OrderStatus.created,
            OrderStatus.inventory_reserved,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order can no longer be cancelled by the customer",
            )
    elif not is_staff_for_store:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only store staff can update this order status",
        )

    transition(order, payload.status)
    db.commit()
    db.refresh(order)
    return order
