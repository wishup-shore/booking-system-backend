from .user import User, UserCreate, UserUpdate
from .accommodation import AccommodationType, AccommodationTypeCreate, AccommodationTypeUpdate, Accommodation, AccommodationCreate, AccommodationUpdate
from .client import Client, ClientCreate, ClientUpdate, ClientGroup, ClientGroupCreate, ClientGroupUpdate, ClientWithStats
from .booking import (
    Booking,
    BookingCreate,
    BookingCreateOpenDates,
    BookingUpdate,
    BookingSetDates,
    BookingPayment,
    BookingCheckIn,
    BookingCheckOut,
    BookingWithDetails,
    CalendarOccupancy,
    CalendarEvent
)

__all__ = [
    # User schemas
    "User", "UserCreate", "UserUpdate",
    # Accommodation schemas
    "AccommodationType", "AccommodationTypeCreate", "AccommodationTypeUpdate",
    "Accommodation", "AccommodationCreate", "AccommodationUpdate",
    # Client schemas
    "Client", "ClientCreate", "ClientUpdate",
    "ClientGroup", "ClientGroupCreate", "ClientGroupUpdate", "ClientWithStats",
    # Booking schemas
    "Booking", "BookingCreate", "BookingCreateOpenDates", "BookingUpdate",
    "BookingSetDates", "BookingPayment", "BookingCheckIn", "BookingCheckOut",
    "BookingWithDetails", "CalendarOccupancy", "CalendarEvent"
]