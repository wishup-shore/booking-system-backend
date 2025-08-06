from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models.accommodation import AccommodationCondition, AccommodationStatus


class AccommodationTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    default_capacity: int
    is_active: bool = True


class AccommodationTypeCreate(AccommodationTypeBase):
    pass


class AccommodationTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_capacity: Optional[int] = None
    is_active: Optional[bool] = None


class AccommodationType(AccommodationTypeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AccommodationBase(BaseModel):
    number: str
    type_id: int
    capacity: int
    price_per_night: Decimal = Field(
        ge=0, description="Price per night must be non-negative"
    )
    status: AccommodationStatus = AccommodationStatus.AVAILABLE
    condition: AccommodationCondition = AccommodationCondition.OK
    comments: Optional[str] = None


class AccommodationCreate(AccommodationBase):
    pass


class AccommodationUpdate(BaseModel):
    number: Optional[str] = None
    type_id: Optional[int] = None
    capacity: Optional[int] = None
    price_per_night: Optional[Decimal] = Field(
        None, ge=0, description="Price per night must be non-negative"
    )
    status: Optional[AccommodationStatus] = None
    condition: Optional[AccommodationCondition] = None
    comments: Optional[str] = None


class Accommodation(AccommodationBase):
    id: int
    created_at: datetime
    type: AccommodationType

    class Config:
        from_attributes = True
