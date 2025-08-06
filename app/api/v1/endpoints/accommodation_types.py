from typing import List

from fastapi import APIRouter

from app.core.common_deps import (
    AccommodationTypeServiceDep,
    CurrentUserDep,
    StaffUserDep,
)
from app.schemas.accommodation import (
    AccommodationType,
    AccommodationTypeCreate,
    AccommodationTypeUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[AccommodationType])
async def get_accommodation_types(
    service: AccommodationTypeServiceDep, current_user: CurrentUserDep
):
    return await service.get_all()


@router.post("/", response_model=AccommodationType)
async def create_accommodation_type(
    accommodation_type_data: AccommodationTypeCreate,
    service: AccommodationTypeServiceDep,
    current_user: StaffUserDep,
):
    return await service.create(accommodation_type_data)


@router.put("/{accommodation_type_id}", response_model=AccommodationType)
async def update_accommodation_type(
    accommodation_type_id: int,
    accommodation_type_data: AccommodationTypeUpdate,
    service: AccommodationTypeServiceDep,
    current_user: StaffUserDep,
):
    return await service.update(accommodation_type_id, accommodation_type_data)


@router.delete("/{accommodation_type_id}")
async def delete_accommodation_type(
    accommodation_type_id: int,
    service: AccommodationTypeServiceDep,
    current_user: StaffUserDep,
):
    await service.delete(accommodation_type_id)
    return {"message": "Accommodation type deleted successfully"}
