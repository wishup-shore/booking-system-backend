from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class CustomItem(Base):
    __tablename__ = "custom_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), default=0.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    booking_assignments = relationship(
        "BookingCustomItem", back_populates="custom_item"
    )


class BookingCustomItem(Base):
    __tablename__ = "booking_custom_items"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    custom_item_id = Column(Integer, ForeignKey("custom_items.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    price_at_booking = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    booking = relationship("Booking", back_populates="custom_items")
    custom_item = relationship("CustomItem", back_populates="booking_assignments")
