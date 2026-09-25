from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.cart.models import Cart, CartItem
from app.cart.schemas import CartItemCreate, CartItemOut, CartItemUpdate, CartOut
from app.catalog.store_product_models import StoreProduct
from app.database.session import get_db
from app.stores.models import Store
from app.users.models import User


router = APIRouter(prefix="/cart", tags=["cart"])


def get_active_store(store_id: UUID, db: Session) -> Store:
    store = db.get(Store, store_id)
    if store is None or not store.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return store


def get_store_product(
    store_id: UUID, store_product_id: UUID, db: Session
) -> StoreProduct:
    statement = select(StoreProduct).where(
        StoreProduct.id == store_product_id,
        StoreProduct.store_id == store_id,
        StoreProduct.is_available.is_(True),
    )
    store_product = db.scalar(statement)
    if store_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Available store product not found",
        )
    return store_product


def get_or_create_cart(user_id: UUID, store_id: UUID, db: Session) -> Cart:
    statement = (
        select(Cart)
        .where(Cart.user_id == user_id, Cart.store_id == store_id)
        .options(selectinload(Cart.items))
    )
    cart = db.scalar(statement)
    if cart is not None:
        return cart

    cart = Cart(user_id=user_id, store_id=store_id)
    db.add(cart)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        cart = db.scalar(statement)
        if cart is None:
            raise
    return cart


def build_cart_response(cart: Cart, db: Session) -> CartOut:
    if not cart.items:
        return CartOut(
            id=cart.id,
            user_id=cart.user_id,
            store_id=cart.store_id,
            created_at=cart.created_at,
            items=[],
            subtotal=Decimal("0.00"),
        )

    product_ids = [item.store_product_id for item in cart.items]
    prices = dict(
        db.execute(
            select(StoreProduct.id, StoreProduct.price).where(
                StoreProduct.id.in_(product_ids)
            )
        ).all()
    )
    items = []
    subtotal = Decimal("0.00")
    for item in cart.items:
        unit_price = prices[item.store_product_id]
        line_total = unit_price * item.quantity
        subtotal += line_total
        items.append(
            CartItemOut(
                id=item.id,
                store_product_id=item.store_product_id,
                quantity=item.quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    return CartOut(
        id=cart.id,
        user_id=cart.user_id,
        store_id=cart.store_id,
        created_at=cart.created_at,
        items=items,
        subtotal=subtotal,
    )


@router.post("/{store_id}/items", response_model=CartOut, status_code=status.HTTP_200_OK)
def add_item(
    store_id: UUID,
    payload: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_active_store(store_id, db)
    get_store_product(store_id, payload.store_product_id, db)
    cart = get_or_create_cart(current_user.id, store_id, db)

    item = next(
        (item for item in cart.items if item.store_product_id == payload.store_product_id),
        None,
    )
    if item is None:
        cart.items.append(
            CartItem(
                store_product_id=payload.store_product_id,
                quantity=payload.quantity,
            )
        )
    else:
        item.quantity += payload.quantity

    db.commit()
    db.refresh(cart)
    return build_cart_response(cart, db)


@router.get("/{store_id}", response_model=CartOut)
def get_cart(
    store_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_active_store(store_id, db)
    statement = (
        select(Cart)
        .where(Cart.user_id == current_user.id, Cart.store_id == store_id)
        .options(selectinload(Cart.items))
    )
    cart = db.scalar(statement)
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found",
        )
    return build_cart_response(cart, db)


@router.patch("/{store_id}/items/{store_product_id}", response_model=CartOut)
def update_item(
    store_id: UUID,
    store_product_id: UUID,
    payload: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_active_store(store_id, db)
    get_store_product(store_id, store_product_id, db)
    statement = (
        select(Cart)
        .where(Cart.user_id == current_user.id, Cart.store_id == store_id)
        .options(selectinload(Cart.items))
    )
    cart = db.scalar(statement)
    item = next(
        (item for item in cart.items if item.store_product_id == store_product_id),
        None,
    ) if cart else None
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )
    item.quantity = payload.quantity
    db.commit()
    db.refresh(cart)
    return build_cart_response(cart, db)


@router.delete("/{store_id}/items/{store_product_id}", response_model=CartOut)
def remove_item(
    store_id: UUID,
    store_product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_active_store(store_id, db)
    statement = select(Cart).where(
        Cart.user_id == current_user.id,
        Cart.store_id == store_id,
    ).options(selectinload(Cart.items))
    cart = db.scalar(statement)
    item = next(
        (item for item in cart.items if item.store_product_id == store_product_id),
        None,
    ) if cart else None
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )
    db.delete(item)
    db.commit()
    db.refresh(cart)
    return build_cart_response(cart, db)


@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(
    store_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_active_store(store_id, db)
    statement = delete(Cart).where(
        Cart.user_id == current_user.id,
        Cart.store_id == store_id,
    )
    db.execute(statement)
    db.commit()
