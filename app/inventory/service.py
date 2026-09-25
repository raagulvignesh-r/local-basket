from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.inventory.models import Inventory


def reserve_quantity(
    db: Session, store_product_id: UUID, requested_qty: int
) -> Inventory | None:
    result = db.execute(
        update(Inventory)
        .where(Inventory.store_product_id == store_product_id)
        .where(
            (Inventory.quantity_on_hand - Inventory.quantity_reserved)
            >= requested_qty
        )
        .values(quantity_reserved=Inventory.quantity_reserved + requested_qty)
    )
    if result.rowcount == 0:
        return None

    return db.scalar(
        select(Inventory).where(Inventory.store_product_id == store_product_id)
    )
