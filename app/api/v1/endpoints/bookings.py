from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_active_user
from app.models.user import User, UserRole
from app.models.booking import BookingStatus
from app.schemas.booking import (
    Booking,
    BookingCreate,
    BookingCreateOpenDates,
    BookingCreateWithItems,
    BookingCreateOpenDatesWithItems,
    BookingUpdate,
    BookingSetDates,
    BookingPayment,
    BookingCheckIn,
    BookingCheckOut,
    BookingWithDetails,
    BookingWithItems,
    BookingWithFullDetails,
    CalendarOccupancy,
    CalendarEvent,
)
from app.schemas.responses import (
    MessageResponse,
    AccommodationAvailabilityResponse,
    AvailableAccommodation,
    CalendarStatistics,
    BookingActionResponse,
)
from app.services.booking_service import BookingService
from app.services.calendar_service import CalendarService

router = APIRouter()


async def require_staff_role(current_user: User = Depends(get_active_user)):
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff role required")
    return current_user


# Basic CRUD operations
@router.get("/", response_model=List[Booking])
async def get_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[BookingStatus] = Query(
        None, description="Filter by booking status"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get list of bookings with optional status filter"""
    service = BookingService(db)
    if status:
        return await service.get_by_status(status, skip, limit)
    return await service.get_all(skip, limit)


@router.post("/", response_model=Booking)
async def create_booking(
    booking_data: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create a new booking"""
    service = BookingService(db)
    return await service.create(booking_data)


@router.get("/{booking_id}", response_model=BookingWithDetails)
async def get_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get booking details with client and accommodation information"""
    service = BookingService(db)
    booking = await service.get_with_details(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.put("/{booking_id}", response_model=Booking)
async def update_booking(
    booking_id: int,
    booking_data: BookingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Update booking details"""
    service = BookingService(db)
    return await service.update(booking_id, booking_data)


@router.delete("/{booking_id}", response_model=MessageResponse)
async def delete_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Delete booking (only if not checked-in or completed)"""
    service = BookingService(db)
    await service.delete(booking_id)
    return MessageResponse(message="Booking deleted successfully")


# Open dates booking operations
@router.post("/open-dates", response_model=Booking)
async def create_open_dates_booking(
    booking_data: BookingCreateOpenDates,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create booking with open dates (flexible dates)"""
    service = BookingService(db)
    return await service.create_open_dates(booking_data)


@router.get("/open", response_model=List[Booking])
async def get_open_dates_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get all open-dates bookings for planning"""
    service = BookingService(db)
    return await service.get_open_dates_bookings(skip, limit)


@router.put("/{booking_id}/set-dates", response_model=Booking)
async def set_booking_dates(
    booking_id: int,
    dates_data: BookingSetDates,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Set dates for an open-dates booking"""
    service = BookingService(db)
    return await service.set_dates(booking_id, dates_data)


# Status management operations
@router.post("/{booking_id}/checkin", response_model=Booking)
async def checkin_booking(
    booking_id: int,
    checkin_data: BookingCheckIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Process check-in for a booking"""
    service = BookingService(db)
    return await service.check_in(booking_id, checkin_data)


@router.post("/{booking_id}/checkout", response_model=Booking)
async def checkout_booking(
    booking_id: int,
    checkout_data: BookingCheckOut,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Process check-out for a booking"""
    service = BookingService(db)
    return await service.check_out(booking_id, checkout_data)


@router.post("/{booking_id}/cancel", response_model=Booking)
async def cancel_booking(
    booking_id: int,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Cancel a booking"""
    service = BookingService(db)
    return await service.cancel(booking_id, reason)


# Payment operations
@router.post("/{booking_id}/payment", response_model=Booking)
async def add_payment(
    booking_id: int,
    payment_data: BookingPayment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Add payment to booking"""
    service = BookingService(db)
    return await service.add_payment(booking_id, payment_data)


# Calendar and availability operations
@router.get("/calendar/occupancy", response_model=List[CalendarOccupancy])
async def get_calendar_occupancy(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get calendar occupancy data for date range"""
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    calendar_service = CalendarService(db)
    return await calendar_service.get_occupancy_for_date_range(start_date, end_date)


@router.get("/calendar/events", response_model=List[CalendarEvent])
async def get_calendar_events(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get calendar events (bookings) for calendar display"""
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    calendar_service = CalendarService(db)
    return await calendar_service.get_calendar_events(start_date, end_date)


@router.get(
    "/calendar/occupancy/{year}/{month}", response_model=List[CalendarOccupancy]
)
async def get_monthly_occupancy(
    year: int = Path(..., ge=2020, le=2030, description="Year"),
    month: int = Path(..., ge=1, le=12, description="Month (1-12)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get calendar occupancy for a specific month"""
    calendar_service = CalendarService(db)
    return await calendar_service.get_occupancy_for_month(year, month)


@router.get("/calendar/statistics", response_model=CalendarStatistics)
async def get_occupancy_statistics(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get occupancy statistics for date range"""
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    calendar_service = CalendarService(db)
    return await calendar_service.get_occupancy_statistics(start_date, end_date)


# Availability checks
@router.get("/availability/accommodations", response_model=List[AvailableAccommodation])
async def get_available_accommodations(
    start_date: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    capacity: Optional[int] = Query(None, ge=1, description="Minimum capacity needed"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get available accommodations for given dates"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=400, detail="Check-out date must be after check-in date"
        )

    calendar_service = CalendarService(db)
    accommodations = await calendar_service.get_available_accommodations(
        start_date, end_date, capacity
    )

    return [
        AvailableAccommodation(
            id=acc.id,
            number=acc.number,
            type_name=acc.type.name if acc.type else "Unknown",
            capacity=acc.capacity,
            price_per_night=acc.price_per_night or 0.0,
            status=acc.status.value,
        )
        for acc in accommodations
    ]


@router.get("/availability/check", response_model=AccommodationAvailabilityResponse)
async def check_accommodation_availability(
    accommodation_id: int = Query(..., description="Accommodation ID"),
    start_date: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Check if specific accommodation is available for given dates"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=400, detail="Check-out date must be after check-in date"
        )

    calendar_service = CalendarService(db)
    is_available = await calendar_service.check_accommodation_availability(
        accommodation_id, start_date, end_date
    )

    return AccommodationAvailabilityResponse(
        accommodation_id=accommodation_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        is_available=is_available,
    )


# Enhanced booking endpoints with inventory and custom items
@router.post("/with-items", response_model=Booking)
async def create_booking_with_items(
    booking_data: BookingCreateWithItems,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create a new booking with inventory and custom items"""
    service = BookingService(db)
    return await service.create_with_items(booking_data)


@router.post("/open-dates/with-items", response_model=Booking)
async def create_open_dates_booking_with_items(
    booking_data: BookingCreateOpenDatesWithItems,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create open-dates booking with inventory and custom items"""
    service = BookingService(db)
    return await service.create_open_dates_with_items(booking_data)


@router.get("/{booking_id}/with-items", response_model=BookingWithItems)
async def get_booking_with_items(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get booking with inventory and custom items"""
    service = BookingService(db)
    booking = await service.get_with_items(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("/{booking_id}/full-details", response_model=BookingWithFullDetails)
async def get_booking_full_details(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get booking with all details including client, accommodation, and items"""
    service = BookingService(db)
    booking = await service.get_with_full_details(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


# Inventory management endpoints
@router.post(
    "/{booking_id}/inventory/{inventory_item_id}", response_model=BookingActionResponse
)
async def add_inventory_item_to_booking(
    booking_id: int,
    inventory_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Add an inventory item to a booking"""
    service = BookingService(db)
    await service.add_inventory_item(booking_id, inventory_item_id)
    return BookingActionResponse(
        message="Inventory item added to booking successfully",
        booking_id=booking_id,
        item_id=inventory_item_id,
    )


@router.delete(
    "/{booking_id}/inventory/{inventory_item_id}", response_model=BookingActionResponse
)
async def remove_inventory_item_from_booking(
    booking_id: int,
    inventory_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Remove an inventory item from a booking"""
    service = BookingService(db)
    await service.remove_inventory_item(booking_id, inventory_item_id)
    return BookingActionResponse(
        message="Inventory item removed from booking successfully",
        booking_id=booking_id,
        item_id=inventory_item_id,
    )


# Custom items management endpoints
@router.post(
    "/{booking_id}/custom-items/{custom_item_id}", response_model=BookingActionResponse
)
async def add_custom_item_to_booking(
    booking_id: int,
    custom_item_id: int,
    quantity: int = Query(1, gt=0, description="Quantity of the custom item"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Add a custom item to a booking"""
    service = BookingService(db)
    await service.add_custom_item(booking_id, custom_item_id, quantity)
    return BookingActionResponse(
        message="Custom item added to booking successfully",
        booking_id=booking_id,
        item_id=custom_item_id,
    )


@router.delete(
    "/custom-items/{booking_custom_item_id}", response_model=BookingActionResponse
)
async def remove_custom_item_from_booking(
    booking_custom_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Remove a custom item from a booking"""
    service = BookingService(db)
    await service.remove_custom_item(booking_custom_item_id)
    return BookingActionResponse(
        message="Custom item removed from booking successfully",
        item_id=booking_custom_item_id,
    )
