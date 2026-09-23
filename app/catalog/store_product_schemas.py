from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StoreProductCreate(BaseModel):
    product_id: UUID
    price: Decimal = Field(gt=0)


class StoreProductUpdate(BaseModel):
    price: Decimal | None = Field(default=None, gt=0)
    is_available: bool | None = None


class StoreProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    store_id: UUID
    product_id: UUID
    price: Decimal
    is_available: bool
    created_at: datetime
