from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.accommodation import AccommodationType, Accommodation
from app.schemas.accommodation import (
    AccommodationTypeCreate,
    AccommodationTypeUpdate,
    AccommodationCreate,
    AccommodationUpdate,
)
from app.core.service_utils import ensure_exists


class AccommodationTypeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[AccommodationType]:
        stmt = select(AccommodationType)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(
        self, accommodation_type_id: int
    ) -> Optional[AccommodationType]:
        stmt = select(AccommodationType).where(
            AccommodationType.id == accommodation_type_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, accommodation_type_data: AccommodationTypeCreate
    ) -> AccommodationType:
        db_accommodation_type = AccommodationType(
            **accommodation_type_data.model_dump()
        )
        self.db.add(db_accommodation_type)
        await self.db.commit()
        await self.db.refresh(db_accommodation_type)
        return db_accommodation_type

    async def update(
        self,
        accommodation_type_id: int,
        accommodation_type_data: AccommodationTypeUpdate,
    ) -> AccommodationType:
        db_accommodation_type = await self.get_by_id(accommodation_type_id)
        db_accommodation_type = ensure_exists(
            db_accommodation_type, "Accommodation type", accommodation_type_id
        )

        update_data = accommodation_type_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_accommodation_type, field, value)

        await self.db.commit()
        await self.db.refresh(db_accommodation_type)
        return db_accommodation_type

    async def delete(self, accommodation_type_id: int) -> bool:
        db_accommodation_type = await self.get_by_id(accommodation_type_id)
        db_accommodation_type = ensure_exists(
            db_accommodation_type, "Accommodation type", accommodation_type_id
        )

        await self.db.delete(db_accommodation_type)
        await self.db.commit()
        return True


class AccommodationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[Accommodation]:
        stmt = select(Accommodation).options(selectinload(Accommodation.type))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, accommodation_id: int) -> Optional[Accommodation]:
        stmt = (
            select(Accommodation)
            .options(selectinload(Accommodation.type))
            .where(Accommodation.id == accommodation_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, accommodation_data: AccommodationCreate) -> Accommodation:
        db_accommodation = Accommodation(**accommodation_data.model_dump())
        self.db.add(db_accommodation)
        await self.db.commit()
        await self.db.refresh(db_accommodation)

        # Eagerly load the type relationship to avoid lazy loading issues during serialization
        stmt = (
            select(Accommodation)
            .options(selectinload(Accommodation.type))
            .where(Accommodation.id == db_accommodation.id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def update(
        self, accommodation_id: int, accommodation_data: AccommodationUpdate
    ) -> Accommodation:
        db_accommodation = await self.get_by_id(accommodation_id)
        db_accommodation = ensure_exists(
            db_accommodation, "Accommodation", accommodation_id
        )

        update_data = accommodation_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_accommodation, field, value)

        await self.db.commit()
        await self.db.refresh(db_accommodation)

        # Eagerly load the type relationship to avoid lazy loading issues during serialization
        stmt = (
            select(Accommodation)
            .options(selectinload(Accommodation.type))
            .where(Accommodation.id == db_accommodation.id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def delete(self, accommodation_id: int) -> bool:
        db_accommodation = await self.get_by_id(accommodation_id)
        db_accommodation = ensure_exists(
            db_accommodation, "Accommodation", accommodation_id
        )

        await self.db.delete(db_accommodation)
        await self.db.commit()
        return True
