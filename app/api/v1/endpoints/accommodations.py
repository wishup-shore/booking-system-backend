from typing import List, Optional

from fastapi import APIRouter, Query

from app.core.common_deps import AccommodationServiceDep, CurrentUserDep, StaffUserDep
from app.models.accommodation import AccommodationStatus
from app.schemas.accommodation import (
    Accommodation,
    AccommodationCreate,
    AccommodationUpdate,
)
from app.schemas.responses import MessageResponse

router = APIRouter()


@router.get("/", response_model=List[Accommodation])
async def get_accommodations(
    service: AccommodationServiceDep,
    current_user: CurrentUserDep,
    type_id: Optional[int] = Query(None, description="Filter by accommodation type ID"),
    status: Optional[AccommodationStatus] = Query(
        None, description="Filter by accommodation status"
    ),
):
    return await service.get_all(type_id=type_id, status=status)


@router.post("/", response_model=Accommodation)
async def create_accommodation(
    accommodation_data: AccommodationCreate,
    service: AccommodationServiceDep,
    current_user: StaffUserDep,
):
    return await service.create(accommodation_data)


@router.put("/{accommodation_id}", response_model=Accommodation)
async def update_accommodation(
    accommodation_id: int,
    accommodation_data: AccommodationUpdate,
    service: AccommodationServiceDep,
    current_user: StaffUserDep,
):
    return await service.update(accommodation_id, accommodation_data)


@router.delete("/{accommodation_id}", response_model=MessageResponse)
async def delete_accommodation(
    accommodation_id: int,
    service: AccommodationServiceDep,
    current_user: StaffUserDep,
):
    await service.delete(accommodation_id)
    return MessageResponse(message="Accommodation deleted successfully")
