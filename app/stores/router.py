from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.stores.models import Store
from app.stores.schemas import StoreCreate, StoreOut, StoreUpdate
from app.users.models import User, UserRole


router = APIRouter(prefix="/stores", tags=["stores"])
admin_required = require_role(UserRole.admin)


@router.post("", response_model=StoreOut, status_code=status.HTTP_201_CREATED)
def create_store(
    payload: StoreCreate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_required),
):
    store = Store(**payload.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("", response_model=list[StoreOut])
def list_stores(db: Session = Depends(get_db)):
    statement = (
        select(Store)
        .where(Store.is_active.is_(True))
        .order_by(Store.name)
    )
    return db.scalars(statement).all()


@router.get("/{store_id}", response_model=StoreOut)
def get_store(store_id: UUID, db: Session = Depends(get_db)):
    statement = select(Store).where(
        Store.id == store_id,
        Store.is_active.is_(True),
    )
    store = db.scalar(statement)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return store


@router.patch("/{store_id}", response_model=StoreOut)
def update_store(
    store_id: UUID,
    payload: StoreUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_required),
):
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, field, value)

    db.commit()
    db.refresh(store)
    return store


@router.delete("/{store_id}", response_model=StoreOut)
def deactivate_store(
    store_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(admin_required),
):
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    store.is_active = False
    db.commit()
    db.refresh(store)
    return store
