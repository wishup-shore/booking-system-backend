from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_item import BookingCustomItem, CustomItem
from app.schemas.custom_item import (
    BookingCustomItemCreate,
    BookingCustomItemUpdate,
    CustomItemCreate,
    CustomItemUpdate,
)


class CustomItemService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # CustomItem CRUD operations
    async def create_custom_item(
        self, custom_item_data: CustomItemCreate
    ) -> CustomItem:
        """Create a new custom item"""
        db_custom_item = CustomItem(**custom_item_data.model_dump())
        self.db.add(db_custom_item)
        await self.db.commit()
        await self.db.refresh(db_custom_item)
        return db_custom_item

    async def get_custom_items(
        self, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> List[CustomItem]:
        """Get list of custom items"""
        query = select(CustomItem)

        if active_only:
            query = query.where(CustomItem.is_active)

        query = query.offset(skip).limit(limit).order_by(CustomItem.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_custom_item(self, custom_item_id: int) -> Optional[CustomItem]:
        """Get custom item by ID"""
        result = await self.db.execute(
            select(CustomItem).where(CustomItem.id == custom_item_id)
        )
        return result.scalar_one_or_none()

    async def update_custom_item(
        self, custom_item_id: int, custom_item_data: CustomItemUpdate
    ) -> CustomItem:
        """Update custom item"""
        db_custom_item = await self.get_custom_item(custom_item_id)
        if not db_custom_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Custom item not found"
            )

        update_data = custom_item_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_custom_item, field, value)

        await self.db.commit()
        await self.db.refresh(db_custom_item)
        return db_custom_item

    async def delete_custom_item(self, custom_item_id: int) -> None:
        """Delete custom item (soft delete by setting is_active=False)"""
        db_custom_item = await self.get_custom_item(custom_item_id)
        if not db_custom_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Custom item not found"
            )

        # Check if there are bookings using this custom item
        result = await self.db.execute(
            select(BookingCustomItem).where(
                BookingCustomItem.custom_item_id == custom_item_id
            )
        )
        if result.scalar_one_or_none():
            # Soft delete if there are bookings using this item
            db_custom_item.is_active = False
            await self.db.commit()
        else:
            # Hard delete if no bookings use this item
            await self.db.delete(db_custom_item)
            await self.db.commit()

    # BookingCustomItem operations
    async def create_booking_custom_item(
        self, booking_id: int, custom_item_data: BookingCustomItemCreate
    ) -> BookingCustomItem:
        """Add a custom item to a booking"""
        # Verify the custom item exists and is active
        custom_item = await self.get_custom_item(custom_item_data.custom_item_id)
        if not custom_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Custom item not found"
            )

        if not custom_item.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom item is not active",
            )

        # Create booking custom item with current price
        db_booking_custom_item = BookingCustomItem(
            booking_id=booking_id,
            custom_item_id=custom_item_data.custom_item_id,
            quantity=custom_item_data.quantity,
            price_at_booking=custom_item.price,  # Lock in current price
        )

        self.db.add(db_booking_custom_item)
        await self.db.commit()
        await self.db.refresh(db_booking_custom_item)
        return db_booking_custom_item

    async def get_booking_custom_items(
        self, booking_id: int
    ) -> List[BookingCustomItem]:
        """Get all custom items for a booking"""
        result = await self.db.execute(
            select(BookingCustomItem).where(BookingCustomItem.booking_id == booking_id)
        )
        return list(result.scalars().all())

    async def get_booking_custom_item(
        self, booking_custom_item_id: int
    ) -> Optional[BookingCustomItem]:
        """Get booking custom item by ID"""
        result = await self.db.execute(
            select(BookingCustomItem).where(
                BookingCustomItem.id == booking_custom_item_id
            )
        )
        return result.scalar_one_or_none()

    async def update_booking_custom_item(
        self,
        booking_custom_item_id: int,
        booking_custom_item_data: BookingCustomItemUpdate,
    ) -> BookingCustomItem:
        """Update booking custom item (typically quantity)"""
        db_booking_custom_item = await self.get_booking_custom_item(
            booking_custom_item_id
        )
        if not db_booking_custom_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking custom item not found",
            )

        update_data = booking_custom_item_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_booking_custom_item, field, value)

        await self.db.commit()
        await self.db.refresh(db_booking_custom_item)
        return db_booking_custom_item

    async def delete_booking_custom_item(self, booking_custom_item_id: int) -> None:
        """Remove custom item from booking"""
        db_booking_custom_item = await self.get_booking_custom_item(
            booking_custom_item_id
        )
        if not db_booking_custom_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking custom item not found",
            )

        await self.db.delete(db_booking_custom_item)
        await self.db.commit()

    async def calculate_custom_items_total(self, booking_id: int) -> Decimal:
        """Calculate total cost of custom items for a booking"""
        booking_custom_items = await self.get_booking_custom_items(booking_id)
        total = Decimal("0.00")

        for item in booking_custom_items:
            total += item.price_at_booking * item.quantity

        return Decimal(str(total))
