import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class InventoryCondition(enum.Enum):
    OK = "ok"
    MINOR_ISSUE = "minor"
    CRITICAL = "critical"


class InventoryType(Base):
    __tablename__ = "inventory_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    items = relationship("InventoryItem", back_populates="type")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, nullable=False, unique=True)
    type_id = Column(Integer, ForeignKey("inventory_types.id"), nullable=False)
    condition = Column(
        Enum(InventoryCondition), default=InventoryCondition.OK, nullable=False
    )
    comments = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    type = relationship("InventoryType", back_populates="items")
    booking_assignments = relationship(
        "BookingInventory", back_populates="inventory_item"
    )


class BookingInventory(Base):
    __tablename__ = "booking_inventory"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    inventory_item_id = Column(
        Integer, ForeignKey("inventory_items.id"), nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    booking = relationship("Booking", back_populates="inventory_items")
    inventory_item = relationship("InventoryItem", back_populates="booking_assignments")
