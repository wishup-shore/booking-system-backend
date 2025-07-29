from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_active_user
from app.models.user import User, UserRole
from app.models.booking import BookingStatus
from app.schemas.booking import (
    Booking, BookingCreate, BookingCreateOpenDates, BookingUpdate, 
    BookingSetDates, BookingPayment, BookingCheckIn, BookingCheckOut,
    BookingWithDetails, CalendarOccupancy, CalendarEvent
)
from app.services.booking_service import BookingService
from app.services.calendar_service import CalendarService

router = APIRouter()


def require_staff_role(current_user: User = Depends(get_active_user)):
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff role required")
    return current_user


# Basic CRUD operations
@router.get("/", response_model=List[Booking])
def get_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[BookingStatus] = Query(None, description="Filter by booking status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    """Get list of bookings with optional status filter"""
    service = BookingService(db)
    if status:
        return service.get_by_status(status, skip, limit)
    return service.get_all(skip, limit)


@router.post("/", response_model=Booking)
def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role)
):
    """Create a new booking"""
    service = BookingService(db)
    return service.create(booking_data)


@router.get("/{booking_id}", response_model=BookingWithDetails)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    """Get booking details with client and accommodation information"""
    service = BookingService(db)
    booking = service.get_with_details(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.put("/{booking_id}", response_model=Booking)
def update_booking(
    booking_id: int,
    booking_data: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role)
):
    """Update booking details"""
    service = BookingService(db)
    return service.update(booking_id, booking_data)


@router.delete("/{booking_id}")
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role)
):
    """Delete booking (only if not checked-in or completed)"""
    service = BookingService(db)
    service.delete(booking_id)
    return {"message": "Booking deleted successfully"}


# Open dates booking operations
@router.post("/open-dates", response_model=Booking)
def create_open_dates_booking(
    booking_data: BookingCreateOpenDates,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role)
):
    """Create booking with open dates (flexible dates)"""
    service = BookingService(db)
    return service.create_open_dates(booking_data)


@router.get("/open", response_model=List[Booking])
def get_open_dates_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    """Get all open-dates bookings for planning"""
    service = BookingService(db)
    return service.get_open_dates_bookings(skip, limit)


@router.put("/{booking_id}/set-dates", response_model=Booking)
def set_booking_dates(
    booking_id: int,
    dates_data: BookingSetDates,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role)
):
    """Set dates for an open-dates booking"""
    service = BookingService(db)
    return service.set_dates(booking_id, dates_data)


# Status management operations
@router.post("/{booking_id}/checkin", response_model=Booking)
def checkin_booking(
    booking_id: int,
    checkin_data: BookingCheckIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role)
):
    """Process check-in for a booking"""
    service = BookingService(db)
    return service.check_in(booking_id, checkin_data)


@router.post("/{booking_id}/checkout", response_model=Booking)
def checkout_booking(
    booking_id: int,
    checkout_data: BookingCheckOut,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role)
):
    """Process check-out for a booking"""
    service = BookingService(db)
    return service.check_out(booking_id, checkout_data)


@router.post("/{booking_id}/cancel", response_model=Booking)
def cancel_booking(
    booking_id: int,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role)
):
    """Cancel a booking"""
    service = BookingService(db)
    return service.cancel(booking_id, reason)


# Payment operations
@router.post("/{booking_id}/payment", response_model=Booking)
def add_payment(
    booking_id: int,
    payment_data: BookingPayment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role)
):
    """Add payment to booking"""
    service = BookingService(db)
    return service.add_payment(booking_id, payment_data)


# Calendar and availability operations
@router.get("/calendar/occupancy", response_model=List[CalendarOccupancy])
def get_calendar_occupancy(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    """Get calendar occupancy data for date range"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=400,
            detail="End date must be after start date"
        )
    
    calendar_service = CalendarService(db)
    return calendar_service.get_occupancy_for_date_range(start_date, end_date)


@router.get("/calendar/events", response_model=List[CalendarEvent])
def get_calendar_events(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    """Get calendar events (bookings) for calendar display"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=400,
            detail="End date must be after start date"
        )
    
    calendar_service = CalendarService(db)
    return calendar_service.get_calendar_events(start_date, end_date)


@router.get("/calendar/occupancy/{year}/{month}", response_model=List[CalendarOccupancy])
def get_monthly_occupancy(
    year: int = Path(..., ge=2020, le=2030, description="Year"),
    month: int = Path(..., ge=1, le=12, description="Month (1-12)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    """Get calendar occupancy for a specific month"""
    calendar_service = CalendarService(db)
    return calendar_service.get_occupancy_for_month(year, month)


@router.get("/calendar/statistics", response_model=dict)
def get_occupancy_statistics(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    """Get occupancy statistics for date range"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=400,
            detail="End date must be after start date"
        )
    
    calendar_service = CalendarService(db)
    return calendar_service.get_occupancy_statistics(start_date, end_date)


# Availability checks
@router.get("/availability/accommodations", response_model=List[dict])
def get_available_accommodations(
    start_date: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    capacity: Optional[int] = Query(None, ge=1, description="Minimum capacity needed"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    """Get available accommodations for given dates"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=400,
            detail="Check-out date must be after check-in date"
        )
    
    calendar_service = CalendarService(db)
    accommodations = calendar_service.get_available_accommodations(start_date, end_date, capacity)
    
    # Format response
    return [
        {
            'id': acc.id,
            'number': acc.number,
            'type_name': acc.type.name if acc.type else 'Unknown',
            'capacity': acc.capacity,
            'price_per_night': float(acc.price_per_night) if acc.price_per_night else 0.0,
            'status': acc.status.value
        }
        for acc in accommodations
    ]


@router.get("/availability/check", response_model=dict)
def check_accommodation_availability(
    accommodation_id: int = Query(..., description="Accommodation ID"),
    start_date: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    """Check if specific accommodation is available for given dates"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=400,
            detail="Check-out date must be after check-in date"
        )
    
    calendar_service = CalendarService(db)
    is_available = calendar_service.check_accommodation_availability(
        accommodation_id, start_date, end_date
    )
    
    return {
        'accommodation_id': accommodation_id,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'is_available': is_available
    }