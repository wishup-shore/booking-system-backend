import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, Numeric
from sqlalchemy.orm import relationship

from app.models.base import Base


class AccommodationStatus(enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    OUT_OF_ORDER = "out_of_order"


class AccommodationCondition(enum.Enum):
    OK = "ok"
    MINOR_ISSUE = "minor"
    CRITICAL = "critical"


class AccommodationType(Base):
    __tablename__ = "accommodation_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    default_capacity = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    accommodations = relationship("Accommodation", back_populates="type")


class Accommodation(Base):
    __tablename__ = "accommodations"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, nullable=False, unique=True)
    type_id = Column(Integer, ForeignKey("accommodation_types.id"), nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(Enum(AccommodationStatus), default=AccommodationStatus.AVAILABLE, nullable=False)
    condition = Column(Enum(AccommodationCondition), default=AccommodationCondition.OK, nullable=False)
    price_per_night = Column(Numeric(10, 2), default=0.0, nullable=False)
    comments = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    type = relationship("AccommodationType", back_populates="accommodations")
    bookings = relationship("Booking", back_populates="accommodation")