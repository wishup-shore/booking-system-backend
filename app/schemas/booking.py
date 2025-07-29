from datetime import datetime, date
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field

from app.models.booking import BookingStatus, PaymentStatus


class BookingBase(BaseModel):
    client_id: int
    accommodation_id: int
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    is_open_dates: bool = False
    guests_count: int = Field(
        gt=0, description="Number of guests must be greater than 0"
    )
    comments: Optional[str] = None


class BookingCreate(BookingBase):
    pass


class BookingCreateOpenDates(BaseModel):
    """Schema for creating open-dates bookings"""

    client_id: int
    accommodation_id: int
    guests_count: int = Field(
        gt=0, description="Number of guests must be greater than 0"
    )
    comments: Optional[str] = None
    is_open_dates: bool = True


class BookingUpdate(BaseModel):
    client_id: Optional[int] = None
    accommodation_id: Optional[int] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    guests_count: Optional[int] = Field(None, gt=0)
    status: Optional[BookingStatus] = None
    payment_status: Optional[PaymentStatus] = None
    total_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    comments: Optional[str] = None


class BookingSetDates(BaseModel):
    """Schema for setting dates on open-dates bookings"""

    check_in_date: date
    check_out_date: date


class BookingPayment(BaseModel):
    """Schema for recording payments"""

    amount: Decimal = Field(gt=0, description="Payment amount must be greater than 0")
    comments: Optional[str] = None


class BookingCheckIn(BaseModel):
    """Schema for check-in process"""

    actual_check_in: Optional[datetime] = None
    comments: Optional[str] = None


class BookingCheckOut(BaseModel):
    """Schema for check-out process"""

    actual_check_out: Optional[datetime] = None
    comments: Optional[str] = None


class Booking(BookingBase):
    id: int
    status: BookingStatus
    payment_status: PaymentStatus
    total_amount: Decimal
    paid_amount: Decimal
    actual_check_in: Optional[datetime] = None
    actual_check_out: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BookingWithDetails(Booking):
    """Booking model with client and accommodation details"""

    client: Optional[dict] = None  # Will be populated with client data
    accommodation: Optional[dict] = None  # Will be populated with accommodation data


class CalendarOccupancy(BaseModel):
    """Schema for calendar occupancy data"""

    date: date
    accommodations: list[dict]  # List of accommodation occupancy for this date


class CalendarEvent(BaseModel):
    """Schema for calendar events/bookings"""

    id: int
    title: str
    start: date
    end: Optional[date] = None
    accommodation_id: int
    accommodation_number: str
    client_name: str
    status: BookingStatus
    is_open_dates: bool
