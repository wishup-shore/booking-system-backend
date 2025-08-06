from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from app.core.common_deps import (
    BookingServiceDep,
    CalendarServiceDep,
    CurrentUserDep,
    StaffUserDep,
)
from app.models.booking import BookingStatus
from app.schemas.booking import (
    Booking,
    BookingCheckIn,
    BookingCheckOut,
    BookingCreate,
    BookingCreateOpenDates,
    BookingCreateOpenDatesWithItems,
    BookingCreateWithItems,
    BookingPayment,
    BookingSetDates,
    BookingUpdate,
    BookingWithDetails,
    BookingWithFullDetails,
    BookingWithItems,
    CalendarEvent,
    CalendarOccupancy,
)
from app.schemas.responses import (
    AccommodationAvailabilityResponse,
    AvailableAccommodation,
    BookingActionResponse,
    CalendarStatistics,
    MessageResponse,
)
from app.schemas.search import BookingSearchRequest

router = APIRouter()


# Basic CRUD operations
@router.get("/", response_model=List[Booking])
async def get_bookings(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[BookingStatus] = Query(
        None, description="Filter by booking status"
    ),
):
    """Get list of bookings with optional status filter"""
    if status:
        return await service.get_by_status(status, skip, limit)
    return await service.get_all(skip, limit)


@router.post("/", response_model=Booking)
async def create_booking(
    booking_data: BookingCreate,
    service: BookingServiceDep,
    current_user: StaffUserDep,
):
    """Create a new booking"""
    return await service.create(booking_data)


@router.get("/{booking_id}", response_model=BookingWithDetails)
async def get_booking(
    booking_id: int,
    service: BookingServiceDep,
    current_user: CurrentUserDep,
):
    """Get booking details with client and accommodation information"""
    booking = await service.get_with_details(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.put("/{booking_id}", response_model=Booking)
async def update_booking(
    booking_id: int,
    booking_data: BookingUpdate,
    service: BookingServiceDep,
    current_user: StaffUserDep,
):
    """Update booking details"""
    return await service.update(booking_id, booking_data)


@router.delete("/{booking_id}", response_model=MessageResponse)
async def delete_booking(
    booking_id: int,
    service: BookingServiceDep,
    current_user: StaffUserDep,
):
    """Delete booking (only if not checked-in or completed)"""
    await service.delete(booking_id)
    return MessageResponse(message="Booking deleted successfully")


# Open dates booking operations
@router.post("/open-dates", response_model=Booking)
async def create_open_dates_booking(
    booking_data: BookingCreateOpenDates,
    service: BookingServiceDep,
    current_user: StaffUserDep,
):
    """Create booking with open dates (flexible dates)"""
    return await service.create_open_dates(booking_data)


@router.get("/open", response_model=List[Booking])
async def get_open_dates_bookings(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get all open-dates bookings for planning"""
    return await service.get_open_dates_bookings(skip, limit)


@router.put("/{booking_id}/set-dates", response_model=Booking)
async def set_booking_dates(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    booking_id: int,
    dates_data: BookingSetDates,
):
    """Set dates for an open-dates booking"""
    return await service.set_dates(booking_id, dates_data)


# Status management operations
@router.post("/{booking_id}/checkin", response_model=Booking)
async def checkin_booking(
    booking_id: int,
    checkin_data: BookingCheckIn,
    service: BookingServiceDep,
    current_user: CurrentUserDep,
):
    """Process check-in for a booking"""
    return await service.check_in(booking_id, checkin_data)


@router.post("/{booking_id}/checkout", response_model=Booking)
async def checkout_booking(
    booking_id: int,
    checkout_data: BookingCheckOut,
    service: BookingServiceDep,
    current_user: CurrentUserDep,
):
    """Process check-out for a booking"""
    return await service.check_out(booking_id, checkout_data)


@router.post("/{booking_id}/cancel", response_model=Booking)
async def cancel_booking(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    booking_id: int,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
):
    """Cancel a booking"""
    return await service.cancel(booking_id, reason)


# Payment operations
@router.post("/{booking_id}/payment", response_model=Booking)
async def add_payment(
    booking_id: int,
    payment_data: BookingPayment,
    service: BookingServiceDep,
    current_user: CurrentUserDep,
):
    """Add payment to booking"""
    return await service.add_payment(booking_id, payment_data)


# Calendar and availability operations
@router.get("/calendar/occupancy", response_model=List[CalendarOccupancy])
async def get_calendar_occupancy(
    calendar_service: CalendarServiceDep,
    current_user: CurrentUserDep,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get calendar occupancy data for date range"""
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    return await calendar_service.get_occupancy_for_date_range(start_date, end_date)


@router.get("/calendar/events", response_model=List[CalendarEvent])
async def get_calendar_events(
    calendar_service: CalendarServiceDep,
    current_user: CurrentUserDep,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get calendar events (bookings) for calendar display"""
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    return await calendar_service.get_calendar_events(start_date, end_date)


@router.get(
    "/calendar/occupancy/{year}/{month}", response_model=List[CalendarOccupancy]
)
async def get_monthly_occupancy(
    calendar_service: CalendarServiceDep,
    current_user: CurrentUserDep,
    year: int = Path(..., ge=2020, le=2030, description="Year"),
    month: int = Path(..., ge=1, le=12, description="Month (1-12)"),
):
    """Get calendar occupancy for a specific month"""
    return await calendar_service.get_occupancy_for_month(year, month)


@router.get("/calendar/statistics", response_model=CalendarStatistics)
async def get_occupancy_statistics(
    calendar_service: CalendarServiceDep,
    current_user: CurrentUserDep,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get occupancy statistics for date range"""
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    return await calendar_service.get_occupancy_statistics(start_date, end_date)


# Availability checks
@router.get("/availability/accommodations", response_model=List[AvailableAccommodation])
async def get_available_accommodations(
    calendar_service: CalendarServiceDep,
    current_user: CurrentUserDep,
    start_date: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    capacity: Optional[int] = Query(None, ge=1, description="Minimum capacity needed"),
):
    """Get available accommodations for given dates"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=400, detail="Check-out date must be after check-in date"
        )

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
    calendar_service: CalendarServiceDep,
    current_user: CurrentUserDep,
    accommodation_id: int = Query(..., description="Accommodation ID"),
    start_date: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
):
    """Check if specific accommodation is available for given dates"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=400, detail="Check-out date must be after check-in date"
        )

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
    service: BookingServiceDep,
    current_user: StaffUserDep,
):
    """Create a new booking with inventory and custom items"""
    return await service.create_with_items(booking_data)


@router.post("/open-dates/with-items", response_model=Booking)
async def create_open_dates_booking_with_items(
    booking_data: BookingCreateOpenDatesWithItems,
    service: BookingServiceDep,
    current_user: StaffUserDep,
):
    """Create open-dates booking with inventory and custom items"""
    return await service.create_open_dates_with_items(booking_data)


@router.get("/{booking_id}/with-items", response_model=BookingWithItems)
async def get_booking_with_items(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    booking_id: int,
):
    """Get booking with inventory and custom items"""
    booking = await service.get_with_items(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("/{booking_id}/full-details", response_model=BookingWithFullDetails)
async def get_booking_full_details(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    booking_id: int,
):
    """Get booking with all details including client, accommodation, and items"""
    booking = await service.get_with_full_details(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


# Inventory management endpoints
@router.post(
    "/{booking_id}/inventory/{inventory_item_id}", response_model=BookingActionResponse
)
async def add_inventory_item_to_booking(
    service: BookingServiceDep,
    current_user: StaffUserDep,
    booking_id: int,
    inventory_item_id: int,
):
    """Add an inventory item to a booking"""
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
    service: BookingServiceDep,
    current_user: StaffUserDep,
    booking_id: int,
    inventory_item_id: int,
):
    """Remove an inventory item from a booking"""
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
    service: BookingServiceDep,
    current_user: StaffUserDep,
    booking_id: int,
    custom_item_id: int,
    quantity: int = Query(1, gt=0, description="Quantity of the custom item"),
):
    """Add a custom item to a booking"""
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
    service: BookingServiceDep,
    current_user: StaffUserDep,
    booking_custom_item_id: int,
):
    """Remove a custom item from a booking"""
    await service.remove_custom_item(booking_custom_item_id)
    return BookingActionResponse(
        message="Custom item removed from booking successfully",
        item_id=booking_custom_item_id,
    )


# Enhanced search endpoints
@router.post("/search", response_model=List[BookingWithDetails])
async def advanced_booking_search(
    search_request: BookingSearchRequest,
    service: BookingServiceDep,
    current_user: CurrentUserDep,
):
    """Advanced booking search with multiple criteria and pagination."""
    result = await service.advanced_search(search_request)
    return result.items


@router.get("/search/by-client-name", response_model=List[BookingWithDetails])
async def search_bookings_by_client_name(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    client_name: str = Query(
        ..., min_length=2, description="Client name to search for"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Search bookings by client name."""
    bookings = await service.search_by_client_name(client_name, skip, limit)

    # Convert to BookingWithDetails format
    detailed_bookings = []
    for booking in bookings:
        detailed_booking = BookingWithDetails(
            **booking.__dict__,
            client=booking.client,
            accommodation=booking.accommodation,
        )
        detailed_bookings.append(detailed_booking)

    return detailed_bookings


@router.get("/search/requiring-attention", response_model=List[BookingWithDetails])
async def get_bookings_requiring_attention(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get bookings that require staff attention."""
    bookings = await service.get_bookings_requiring_attention(skip, limit)

    # Convert to BookingWithDetails format
    detailed_bookings = []
    for booking in bookings:
        detailed_booking = BookingWithDetails(
            **booking.__dict__,
            client=booking.client,
            accommodation=booking.accommodation,
        )
        detailed_bookings.append(detailed_booking)

    return detailed_bookings


@router.get("/analytics/revenue")
async def get_revenue_analytics(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    start_date: date = Query(..., description="Start date for revenue analysis"),
    end_date: date = Query(..., description="End date for revenue analysis"),
    include_pending: bool = Query(
        False, description="Include pending bookings in calculations"
    ),
):
    """Get revenue analytics for date range."""
    return await service.get_revenue_by_date_range(
        start_date, end_date, include_pending
    )


@router.get("/analytics/occupancy")
async def get_occupancy_analytics(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    start_date: date = Query(..., description="Start date for occupancy analysis"),
    end_date: date = Query(..., description="End date for occupancy analysis"),
):
    """Get occupancy analytics for date range."""
    return await service.get_occupancy_statistics(start_date, end_date)


@router.get("/search/date-range-status", response_model=List[BookingWithDetails])
async def search_bookings_by_date_and_status(
    service: BookingServiceDep,
    current_user: CurrentUserDep,
    start_date: date = Query(..., description="Start date for search"),
    end_date: date = Query(..., description="End date for search"),
    statuses: List[BookingStatus] = Query(
        ..., description="Booking statuses to filter by"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Search bookings by date range and status."""
    bookings = await service.search_by_date_range_and_status(
        start_date, end_date, statuses, skip, limit
    )

    # Convert to BookingWithDetails format
    detailed_bookings = []
    for booking in bookings:
        detailed_booking = BookingWithDetails(
            **booking.__dict__,
            client=booking.client,
            accommodation=booking.accommodation,
        )
        detailed_bookings.append(detailed_booking)

    return detailed_bookings
