from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class CustomItemBase(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the custom item/service")
    description: Optional[str] = None
    price: Decimal = Field(ge=0, description="Price of the custom item")
    is_active: bool = True


class CustomItemCreate(CustomItemBase):
    pass


class CustomItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CustomItem(CustomItemBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BookingCustomItemCreate(BaseModel):
    custom_item_id: int
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")


class BookingCustomItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)


class BookingCustomItem(BaseModel):
    id: int
    booking_id: int
    custom_item_id: int
    quantity: int
    price_at_booking: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class BookingCustomItemWithDetails(BookingCustomItem):
    """Booking custom item with custom item details"""

    custom_item: Optional[CustomItem] = None
