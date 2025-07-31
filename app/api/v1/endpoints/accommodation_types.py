from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_active_user
from app.models.user import User, UserRole
from app.schemas.accommodation import (
    AccommodationType,
    AccommodationTypeCreate,
    AccommodationTypeUpdate,
)
from app.services.accommodation_service import AccommodationTypeService

router = APIRouter()


def require_staff_role(current_user: User = Depends(get_active_user)):
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff role required")
    return current_user


@router.get("/", response_model=List[AccommodationType])
def get_accommodation_types(
    db: Session = Depends(get_db), current_user: User = Depends(get_active_user)
):
    service = AccommodationTypeService(db)
    return service.get_all()


@router.post("/", response_model=AccommodationType)
def create_accommodation_type(
    accommodation_type_data: AccommodationTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = AccommodationTypeService(db)
    return service.create(accommodation_type_data)


@router.put("/{accommodation_type_id}", response_model=AccommodationType)
def update_accommodation_type(
    accommodation_type_id: int,
    accommodation_type_data: AccommodationTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = AccommodationTypeService(db)
    return service.update(accommodation_type_id, accommodation_type_data)

@router.delete("/{accommodation_type_id}")
def delete_accommodation_type(
    accommodation_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = AccommodationTypeService(db)
    return service.delete(accommodation_type_id)
