from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.accommodation import AccommodationType, Accommodation
from app.schemas.accommodation import (
    AccommodationTypeCreate,
    AccommodationTypeUpdate,
    AccommodationCreate,
    AccommodationUpdate,
)


class AccommodationTypeService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[AccommodationType]:
        return self.db.query(AccommodationType).all()

    def get_by_id(self, accommodation_type_id: int) -> Optional[AccommodationType]:
        return (
            self.db.query(AccommodationType)
            .filter(AccommodationType.id == accommodation_type_id)
            .first()
        )

    def create(
        self, accommodation_type_data: AccommodationTypeCreate
    ) -> AccommodationType:
        db_accommodation_type = AccommodationType(
            **accommodation_type_data.model_dump()
        )
        self.db.add(db_accommodation_type)
        self.db.commit()
        self.db.refresh(db_accommodation_type)
        return db_accommodation_type

    def update(
        self,
        accommodation_type_id: int,
        accommodation_type_data: AccommodationTypeUpdate,
    ) -> AccommodationType:
        db_accommodation_type = self.get_by_id(accommodation_type_id)
        if not db_accommodation_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accommodation type not found",
            )

        update_data = accommodation_type_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_accommodation_type, field, value)

        self.db.commit()
        self.db.refresh(db_accommodation_type)
        return db_accommodation_type
    
    def delete(self, accommodation_type_id: int) -> bool:
        db_accommodation_type = self.get_by_id(accommodation_type_id)
        if not db_accommodation_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accommodation type not found",
            )

        self.db.delete(db_accommodation_type)
        self.db.commit()
        return True


class AccommodationService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Accommodation]:
        return self.db.query(Accommodation).all()

    def get_by_id(self, accommodation_id: int) -> Optional[Accommodation]:
        return (
            self.db.query(Accommodation)
            .filter(Accommodation.id == accommodation_id)
            .first()
        )

    def create(self, accommodation_data: AccommodationCreate) -> Accommodation:
        db_accommodation = Accommodation(**accommodation_data.model_dump())
        self.db.add(db_accommodation)
        self.db.commit()
        self.db.refresh(db_accommodation)
        return db_accommodation

    def update(
        self, accommodation_id: int, accommodation_data: AccommodationUpdate
    ) -> Accommodation:
        db_accommodation = self.get_by_id(accommodation_id)
        if not db_accommodation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Accommodation not found"
            )

        update_data = accommodation_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_accommodation, field, value)

        self.db.commit()
        self.db.refresh(db_accommodation)
        return db_accommodation

    def delete(self, accommodation_id: int) -> bool:
        db_accommodation = self.get_by_id(accommodation_id)
        if not db_accommodation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Accommodation not found"
            )

        self.db.delete(db_accommodation)
        self.db.commit()
        return True
