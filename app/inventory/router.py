from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_store_product_access
from app.database.session import get_db
from app.inventory.models import Inventory
from app.inventory.schemas import InventoryOut, InventoryUpdate, ReserveRequest
from app.users.models import User


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.put("/{store_product_id}", response_model=InventoryOut)
def update_inventory(
    store_product_id: UUID,
    payload: InventoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_store_product_access),
):
    inventory = db.scalar(
        select(Inventory).where(Inventory.store_product_id == store_product_id)
    )
    if inventory is None:
        inventory = Inventory(
            store_product_id=store_product_id,
            quantity_on_hand=payload.quantity_on_hand,
        )
        db.add(inventory)
    elif payload.quantity_on_hand < inventory.quantity_reserved:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Quantity on hand cannot be below quantity reserved",
        )
    else:
        inventory.quantity_on_hand = payload.quantity_on_hand

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory already exists for this store product",
        ) from None
    db.refresh(inventory)
    return inventory


@router.post("/{store_product_id}/reserve", response_model=InventoryOut)
def reserve_inventory(
    store_product_id: UUID,
    payload: ReserveRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    inventory = db.scalar(
        select(Inventory).where(Inventory.store_product_id == store_product_id)
    )
    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    result = db.execute(
        update(Inventory)
        .where(Inventory.store_product_id == store_product_id)
        .where(
            (Inventory.quantity_on_hand - Inventory.quantity_reserved)
            >= payload.requested_qty
        )
        .values(quantity_reserved=Inventory.quantity_reserved + payload.requested_qty)
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient stock",
        )

    db.commit()
    db.refresh(inventory)
    return inventory
