from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CartItemCreate(BaseModel):
    store_product_id: UUID
    quantity: int = Field(gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    store_product_id: UUID
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class CartOut(BaseModel):
    id: UUID
    user_id: UUID
    store_id: UUID
    created_at: datetime
    items: list[CartItemOut]
    subtotal: Decimal
