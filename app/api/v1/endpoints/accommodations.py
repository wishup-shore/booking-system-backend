from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_active_user
from app.models.user import User, UserRole
from app.schemas.accommodation import (
    Accommodation,
    AccommodationCreate,
    AccommodationUpdate,
)
from app.services.accommodation_service import AccommodationService

router = APIRouter()


def require_staff_role(current_user: User = Depends(get_active_user)):
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff role required")
    return current_user


@router.get("/", response_model=List[Accommodation])
def get_accommodations(
    db: Session = Depends(get_db), current_user: User = Depends(get_active_user)
):
    service = AccommodationService(db)
    return service.get_all()


@router.post("/", response_model=Accommodation)
def create_accommodation(
    accommodation_data: AccommodationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = AccommodationService(db)
    return service.create(accommodation_data)


@router.put("/{accommodation_id}", response_model=Accommodation)
def update_accommodation(
    accommodation_id: int,
    accommodation_data: AccommodationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = AccommodationService(db)
    return service.update(accommodation_id, accommodation_data)


@router.delete("/{accommodation_id}")
def delete_accommodation(
    accommodation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = AccommodationService(db)
    service.delete(accommodation_id)
    return {"message": "Accommodation deleted successfully"}
