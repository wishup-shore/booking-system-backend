from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.common_deps import (
    ClientGroupServiceDep,
    ClientServiceDep,
    CurrentUserDep,
    StaffUserDep,
)
from app.schemas.client import (
    Client,
    ClientCreate,
    ClientGroup,
    ClientGroupCreate,
    ClientGroupUpdate,
    ClientUpdate,
    ClientWithStats,
)
from app.schemas.responses import MessageResponse
from app.schemas.search import ClientSearchRequest

router = APIRouter()


# Client endpoints
@router.get("/", response_model=List[Client])
async def get_clients(
    service: ClientServiceDep,
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Search by name, phone, or email"),
):
    if search:
        return await service.search_clients(search, skip, limit)
    return await service.get_all(skip, limit)


@router.post("/", response_model=Client)
async def create_client(
    client_data: ClientCreate,
    service: ClientServiceDep,
    current_user: StaffUserDep,
):
    return await service.create(client_data)


@router.get("/{client_id}", response_model=Client)
async def get_client(
    client_id: int,
    service: ClientServiceDep,
    current_user: CurrentUserDep,
):
    client = await service.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=Client)
async def update_client(
    client_id: int,
    client_data: ClientUpdate,
    service: ClientServiceDep,
    current_user: StaffUserDep,
):
    return await service.update(client_id, client_data)


@router.delete("/{client_id}", response_model=MessageResponse)
async def delete_client(
    client_id: int,
    service: ClientServiceDep,
    current_user: StaffUserDep,
):
    await service.delete(client_id)
    return MessageResponse(message="Client deleted successfully")


@router.get("/{client_id}/stats", response_model=ClientWithStats)
async def get_client_stats(
    client_id: int,
    service: ClientServiceDep,
    current_user: CurrentUserDep,
):
    return await service.get_client_stats(client_id)


# Client Group endpoints
@router.get("/groups/", response_model=List[ClientGroup])
async def get_client_groups(
    service: ClientGroupServiceDep, current_user: CurrentUserDep
):
    return await service.get_all()


@router.post("/groups/", response_model=ClientGroup)
async def create_client_group(
    group_data: ClientGroupCreate,
    service: ClientGroupServiceDep,
    current_user: StaffUserDep,
):
    return await service.create(group_data)


@router.get("/groups/{group_id}", response_model=ClientGroup)
async def get_client_group(
    group_id: int,
    service: ClientGroupServiceDep,
    current_user: CurrentUserDep,
):
    group = await service.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Client group not found")
    return group


@router.put("/groups/{group_id}", response_model=ClientGroup)
async def update_client_group(
    group_id: int,
    group_data: ClientGroupUpdate,
    service: ClientGroupServiceDep,
    current_user: StaffUserDep,
):
    return await service.update(group_id, group_data)


@router.delete("/groups/{group_id}", response_model=MessageResponse)
async def delete_client_group(
    group_id: int,
    service: ClientGroupServiceDep,
    current_user: StaffUserDep,
):
    await service.delete(group_id)
    return MessageResponse(message="Client group deleted successfully")


# Enhanced search endpoints
@router.post("/search", response_model=List[Client])
async def advanced_client_search(
    search_request: ClientSearchRequest,
    service: ClientServiceDep,
    current_user: CurrentUserDep,
):
    """Advanced client search with multiple criteria and pagination."""
    result = await service.advanced_search(search_request)
    return result.items


@router.get("/search/by-rating", response_model=List[Client])
async def search_clients_by_rating(
    service: ClientServiceDep,
    current_user: CurrentUserDep,
    min_rating: float = Query(0.0, ge=0.0, le=5.0),
    max_rating: float = Query(5.0, ge=0.0, le=5.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Search clients by rating range."""
    return await service.search_by_rating_range(min_rating, max_rating, skip, limit)


@router.get("/search/with-bookings", response_model=List[Client])
async def search_clients_with_bookings(
    service: ClientServiceDep,
    current_user: CurrentUserDep,
    booking_statuses: Optional[List[str]] = Query(
        None, description="Booking statuses to filter by"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Search clients who have bookings, optionally filtered by booking status."""
    from app.models.booking import BookingStatus

    status_enums = None
    if booking_statuses:
        status_enums = [BookingStatus(status) for status in booking_statuses]

    return await service.search_clients_with_bookings(status_enums, skip, limit)


@router.get("/search/without-bookings", response_model=List[Client])
async def search_clients_without_bookings(
    service: ClientServiceDep,
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get clients who have never made a booking."""
    return await service.get_clients_without_bookings(skip, limit)


@router.get("/search/by-group", response_model=List[Client])
async def search_clients_by_group(
    service: ClientServiceDep,
    current_user: CurrentUserDep,
    group_ids: List[int] = Query(..., description="Group IDs to filter by"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Search clients by group membership."""
    return await service.search_clients_by_group(group_ids, skip, limit)


@router.get("/search/by-car-number", response_model=List[Client])
async def search_clients_by_car_number(
    service: ClientServiceDep,
    current_user: CurrentUserDep,
    car_number: str = Query(..., min_length=3, description="Car number to search for"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Search clients by car number."""
    return await service.search_clients_by_car_number(car_number, skip, limit)


# Analytics endpoints
@router.get("/analytics/top-spenders")
async def get_top_clients_by_spending(
    service: ClientServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(10, ge=1, le=50, description="Number of top clients to return"),
):
    """Get top clients by total spending."""
    return await service.get_top_clients_by_spending(limit)


@router.get("/{client_id}/statistics")
async def get_detailed_client_statistics(
    client_id: int,
    service: ClientServiceDep,
    current_user: CurrentUserDep,
):
    """Get detailed statistics for a specific client."""
    return await service.get_client_statistics_detailed(client_id)


@router.get("/{client_id}/booking-summary")
async def get_client_booking_summary(
    client_id: int,
    service: ClientServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(
        10, ge=1, le=50, description="Number of recent bookings to include"
    ),
):
    """Get a summary of recent bookings for a client."""
    return await service.get_client_booking_summary(client_id, limit)
