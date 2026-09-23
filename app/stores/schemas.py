from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StoreCreate(BaseModel):
    name: str
    address: str
    city: str


class StoreUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    is_active: bool | None = None


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str
    city: str
    is_active: bool
    created_at: datetime
