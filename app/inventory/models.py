import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    store_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("store_products.id"), unique=True, nullable=False
    )
    quantity_on_hand: Mapped[int] = mapped_column(nullable=False, default=0)
    quantity_reserved: Mapped[int] = mapped_column(nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    @property
    def quantity_available(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved
