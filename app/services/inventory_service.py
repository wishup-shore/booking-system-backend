from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.inventory import InventoryType, InventoryItem, BookingInventory
from app.schemas.inventory import (
    InventoryTypeCreate,
    InventoryTypeUpdate,
    InventoryItemCreate,
    InventoryItemUpdate,
)


class InventoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # InventoryType CRUD operations
    async def create_inventory_type(
        self, inventory_type_data: InventoryTypeCreate
    ) -> InventoryType:
        """Create a new inventory type"""
        db_inventory_type = InventoryType(**inventory_type_data.model_dump())
        self.db.add(db_inventory_type)
        await self.db.commit()
        await self.db.refresh(db_inventory_type)
        return db_inventory_type

    async def get_inventory_types(
        self, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> List[InventoryType]:
        """Get list of inventory types"""
        query = select(InventoryType)

        if active_only:
            query = query.where(InventoryType.is_active)

        query = query.offset(skip).limit(limit).order_by(InventoryType.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_inventory_type(
        self, inventory_type_id: int
    ) -> Optional[InventoryType]:
        """Get inventory type by ID"""
        result = await self.db.execute(
            select(InventoryType).where(InventoryType.id == inventory_type_id)
        )
        return result.scalar_one_or_none()

    async def update_inventory_type(
        self, inventory_type_id: int, inventory_type_data: InventoryTypeUpdate
    ) -> InventoryType:
        """Update inventory type"""
        db_inventory_type = await self.get_inventory_type(inventory_type_id)
        if not db_inventory_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inventory type not found"
            )

        update_data = inventory_type_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_inventory_type, field, value)

        await self.db.commit()
        await self.db.refresh(db_inventory_type)
        return db_inventory_type

    async def delete_inventory_type(self, inventory_type_id: int) -> None:
        """Delete inventory type (soft delete by setting is_active=False)"""
        db_inventory_type = await self.get_inventory_type(inventory_type_id)
        if not db_inventory_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inventory type not found"
            )

        # Check if there are items of this type
        result = await self.db.execute(
            select(InventoryItem).where(InventoryItem.type_id == inventory_type_id)
        )
        if result.scalar_one_or_none():
            # Soft delete if there are items
            db_inventory_type.is_active = False
            await self.db.commit()
        else:
            # Hard delete if no items
            await self.db.delete(db_inventory_type)
            await self.db.commit()

    # InventoryItem CRUD operations
    async def create_inventory_item(
        self, inventory_item_data: InventoryItemCreate
    ) -> InventoryItem:
        """Create a new inventory item"""
        # Verify the inventory type exists
        inventory_type = await self.get_inventory_type(inventory_item_data.type_id)
        if not inventory_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inventory type not found",
            )

        # Check if item number is unique
        existing_item = await self.get_inventory_item_by_number(
            inventory_item_data.number
        )
        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inventory item with this number already exists",
            )

        db_inventory_item = InventoryItem(**inventory_item_data.model_dump())
        self.db.add(db_inventory_item)
        await self.db.commit()
        await self.db.refresh(db_inventory_item)
        return db_inventory_item

    async def get_inventory_items(
        self,
        skip: int = 0,
        limit: int = 100,
        type_id: Optional[int] = None,
        available_only: bool = False,
    ) -> List[InventoryItem]:
        """Get list of inventory items"""
        query = select(InventoryItem).options(selectinload(InventoryItem.type))

        if type_id:
            query = query.where(InventoryItem.type_id == type_id)

        if available_only:
            # Items that are not currently assigned to any active booking
            query = query.where(
                ~InventoryItem.id.in_(
                    select(BookingInventory.inventory_item_id).join(
                        InventoryItem.booking_assignments
                    )
                )
            )

        query = query.offset(skip).limit(limit).order_by(InventoryItem.number)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_inventory_item(
        self, inventory_item_id: int
    ) -> Optional[InventoryItem]:
        """Get inventory item by ID"""
        result = await self.db.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.type))
            .where(InventoryItem.id == inventory_item_id)
        )
        return result.scalar_one_or_none()

    async def get_inventory_item_by_number(
        self, number: str
    ) -> Optional[InventoryItem]:
        """Get inventory item by number"""
        result = await self.db.execute(
            select(InventoryItem).where(InventoryItem.number == number)
        )
        return result.scalar_one_or_none()

    async def update_inventory_item(
        self, inventory_item_id: int, inventory_item_data: InventoryItemUpdate
    ) -> InventoryItem:
        """Update inventory item"""
        db_inventory_item = await self.get_inventory_item(inventory_item_id)
        if not db_inventory_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
            )

        update_data = inventory_item_data.model_dump(exclude_unset=True)

        # Check if updating number and ensure uniqueness
        if "number" in update_data:
            existing_item = await self.get_inventory_item_by_number(
                update_data["number"]
            )
            if existing_item and existing_item.id != inventory_item_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inventory item with this number already exists",
                )

        # Verify inventory type exists if updating type_id
        if "type_id" in update_data:
            inventory_type = await self.get_inventory_type(update_data["type_id"])
            if not inventory_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inventory type not found",
                )

        for field, value in update_data.items():
            setattr(db_inventory_item, field, value)

        await self.db.commit()
        await self.db.refresh(db_inventory_item)
        return db_inventory_item

    async def delete_inventory_item(self, inventory_item_id: int) -> None:
        """Delete inventory item"""
        db_inventory_item = await self.get_inventory_item(inventory_item_id)
        if not db_inventory_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
            )

        # Check if item is assigned to any bookings
        result = await self.db.execute(
            select(BookingInventory).where(
                BookingInventory.inventory_item_id == inventory_item_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete inventory item that is assigned to bookings",
            )

        await self.db.delete(db_inventory_item)
        await self.db.commit()

    async def get_available_items_by_type(self, type_id: int) -> List[InventoryItem]:
        """Get available inventory items of a specific type"""
        return await self.get_inventory_items(
            type_id=type_id, available_only=True, limit=1000
        )
