from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import require_store_access
from app.catalog.models import Product
from app.catalog.store_product_models import StoreProduct
from app.catalog.store_product_schemas import (
    StoreProductCreate,
    StoreProductOut,
    StoreProductUpdate,
)
from app.database.session import get_db
from app.stores.models import Store
from app.users.models import User


router = APIRouter(prefix="/stores/{store_id}/products", tags=["store-products"])


def get_active_store(store_id: UUID, db: Session) -> Store:
    store = db.get(Store, store_id)
    if store is None or not store.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return store


@router.post("", response_model=StoreProductOut, status_code=status.HTTP_201_CREATED)
def add_product_to_store(
    store_id: UUID,
    payload: StoreProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_store_access),
):
    get_active_store(store_id, db)
    product = db.get(Product, payload.product_id)
    if product is None or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    store_product = StoreProduct(
        store_id=store_id,
        **payload.model_dump(),
    )
    db.add(store_product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product is already listed for this store",
        ) from None
    db.refresh(store_product)
    return store_product


@router.get("", response_model=list[StoreProductOut])
def list_store_products(store_id: UUID, db: Session = Depends(get_db)):
    get_active_store(store_id, db)
    statement = select(StoreProduct).where(
        StoreProduct.store_id == store_id,
        StoreProduct.is_available.is_(True),
    )
    return db.scalars(statement).all()


@router.patch("/{store_product_id}", response_model=StoreProductOut)
def update_store_product(
    store_id: UUID,
    store_product_id: UUID,
    payload: StoreProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_store_access),
):
    get_active_store(store_id, db)
    statement = select(StoreProduct).where(
        StoreProduct.id == store_product_id,
        StoreProduct.store_id == store_id,
    )
    store_product = db.scalar(statement)
    if store_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store product not found",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store_product, field, value)

    db.commit()
    db.refresh(store_product)
    return store_product


@router.delete("/{store_product_id}", response_model=StoreProductOut)
def remove_product_from_store(
    store_id: UUID,
    store_product_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_store_access),
):
    get_active_store(store_id, db)
    statement = select(StoreProduct).where(
        StoreProduct.id == store_product_id,
        StoreProduct.store_id == store_id,
    )
    store_product = db.scalar(statement)
    if store_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store product not found",
        )

    db.delete(store_product)
    db.commit()
    return store_product
