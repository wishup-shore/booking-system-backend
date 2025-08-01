import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Text,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Enum,
    Numeric,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class BookingStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class PaymentStatus(enum.Enum):
    NOT_PAID = "not_paid"
    PARTIAL = "partial"
    PAID = "paid"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    accommodation_id = Column(Integer, ForeignKey("accommodations.id"), nullable=False)

    # Date fields - nullable for open dates bookings
    check_in_date = Column(Date, nullable=True)
    check_out_date = Column(Date, nullable=True)
    is_open_dates = Column(Boolean, default=False, nullable=False)

    # Actual check-in/out times (when they actually arrive/leave)
    actual_check_in = Column(DateTime, nullable=True)
    actual_check_out = Column(DateTime, nullable=True)

    # Booking details
    guests_count = Column(Integer, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    payment_status = Column(
        Enum(PaymentStatus), default=PaymentStatus.NOT_PAID, nullable=False
    )

    # Financial information
    total_amount = Column(Numeric(10, 2), default=0.0, nullable=False)
    paid_amount = Column(Numeric(10, 2), default=0.0, nullable=False)

    # Additional information
    comments = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    client = relationship("Client", back_populates="bookings")
    accommodation = relationship("Accommodation", back_populates="bookings")
    inventory_items = relationship("BookingInventory", back_populates="booking")
    custom_items = relationship("BookingCustomItem", back_populates="booking")
