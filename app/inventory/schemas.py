from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InventoryUpdate(BaseModel):
    quantity_on_hand: int = Field(ge=0)


class ReserveRequest(BaseModel):
    requested_qty: int = Field(gt=0)


class InventoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    store_product_id: UUID
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    updated_at: datetime
