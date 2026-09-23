from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.catalog.models import Product
from app.catalog.schemas import ProductCreate, ProductOut, ProductUpdate
from app.database.session import get_db
from app.users.models import User, UserRole


router = APIRouter(prefix="/products", tags=["products"])
admin_required = require_role(UserRole.admin)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_required),
):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductOut])
def list_products(
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    statement = select(Product).where(Product.is_active.is_(True))
    if category is not None:
        statement = statement.where(Product.category == category)
    statement = statement.order_by(Product.name)
    return db.scalars(statement).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    statement = select(Product).where(
        Product.id == product_id,
        Product.is_active.is_(True),
    )
    product = db.scalar(statement)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_required),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=ProductOut)
def deactivate_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(admin_required),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    product.is_active = False
    db.commit()
    db.refresh(product)
    return product
