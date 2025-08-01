from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.inventory import InventoryCondition


class InventoryTypeBase(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the inventory type")
    is_active: bool = True


class InventoryTypeCreate(InventoryTypeBase):
    pass


class InventoryTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class InventoryType(InventoryTypeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryItemBase(BaseModel):
    number: str = Field(
        ..., min_length=1, description="Unique number/identifier for the item"
    )
    type_id: int = Field(..., description="ID of the inventory type")
    condition: InventoryCondition = InventoryCondition.OK
    comments: Optional[str] = None


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    number: Optional[str] = Field(None, min_length=1)
    type_id: Optional[int] = None
    condition: Optional[InventoryCondition] = None
    comments: Optional[str] = None


class InventoryItem(InventoryItemBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryItemWithType(InventoryItem):
    """Inventory item with type details"""

    type: Optional[InventoryType] = None


class BookingInventoryCreate(BaseModel):
    inventory_item_id: int


class BookingInventory(BaseModel):
    id: int
    booking_id: int
    inventory_item_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BookingInventoryWithItem(BookingInventory):
    """Booking inventory with item details"""

    inventory_item: Optional[InventoryItemWithType] = None
