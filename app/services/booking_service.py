from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, or_, func
from fastapi import HTTPException, status

from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.models.client import Client
from app.models.accommodation import Accommodation
from app.schemas.booking import (
    BookingCreate,
    BookingCreateOpenDates,
    BookingCreateWithItems,
    BookingCreateOpenDatesWithItems,
    BookingUpdate,
    BookingSetDates,
    BookingPayment,
    BookingCheckIn,
    BookingCheckOut,
    BookingWithDetails,
    BookingWithItems,
    BookingWithFullDetails,
)
from app.models.inventory import InventoryItem, BookingInventory
from app.models.custom_item import BookingCustomItem
from app.services.inventory_service import InventoryService
from app.services.custom_item_service import CustomItemService


class BookingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Booking]:
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.client),
                selectinload(Booking.accommodation).selectinload(Accommodation.type),
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, booking_id: int) -> Optional[Booking]:
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.client),
                selectinload(Booking.accommodation).selectinload(Accommodation.type),
            )
            .where(Booking.id == booking_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_status(
        self, status: BookingStatus, skip: int = 0, limit: int = 100
    ) -> List[Booking]:
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.client),
                selectinload(Booking.accommodation).selectinload(Accommodation.type),
            )
            .where(Booking.status == status)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_open_dates_bookings(
        self, skip: int = 0, limit: int = 100
    ) -> List[Booking]:
        """Get all bookings with open dates"""
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.client),
                selectinload(Booking.accommodation).selectinload(Accommodation.type),
            )
            .where(Booking.is_open_dates)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_bookings_by_date_range(
        self, start_date: date, end_date: date
    ) -> List[Booking]:
        """Get bookings within a date range"""
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.client),
                selectinload(Booking.accommodation).selectinload(Accommodation.type),
            )
            .where(
                and_(
                    not Booking.is_open_dates,  # Only bookings with confirmed dates
                    or_(
                        and_(
                            Booking.check_in_date <= end_date,
                            Booking.check_out_date >= start_date,
                        ),
                        and_(
                            Booking.check_in_date >= start_date,
                            Booking.check_in_date <= end_date,
                        ),
                        and_(
                            Booking.check_out_date >= start_date,
                            Booking.check_out_date <= end_date,
                        ),
                    ),
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def check_availability(
        self,
        accommodation_id: int,
        check_in: date,
        check_out: date,
        exclude_booking_id: Optional[int] = None,
    ) -> bool:
        """Check if accommodation is available for given dates"""
        conditions = [
            Booking.accommodation_id == accommodation_id,
            not Booking.is_open_dates,  # Only bookings with confirmed dates
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]),
            or_(
                and_(
                    Booking.check_in_date <= check_out,
                    Booking.check_out_date >= check_in,
                ),
                and_(
                    Booking.check_in_date >= check_in,
                    Booking.check_in_date <= check_out,
                ),
                and_(
                    Booking.check_out_date >= check_in,
                    Booking.check_out_date <= check_out,
                ),
            ),
        ]

        if exclude_booking_id:
            conditions.append(Booking.id != exclude_booking_id)

        stmt = select(func.count(Booking.id)).where(and_(*conditions))
        result = await self.db.execute(stmt)
        count = result.scalar()
        return count == 0

    async def create(self, booking_data: BookingCreate) -> Booking:
        # Validate client exists
        client_stmt = select(Client).where(Client.id == booking_data.client_id)
        client_result = await self.db.execute(client_stmt)
        client = client_result.scalar_one_or_none()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
            )

        # Validate accommodation exists
        accommodation_stmt = select(Accommodation).where(
            Accommodation.id == booking_data.accommodation_id
        )
        accommodation_result = await self.db.execute(accommodation_stmt)
        accommodation = accommodation_result.scalar_one_or_none()
        if not accommodation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Accommodation not found"
            )

        # For regular bookings, check availability and validate dates
        if not booking_data.is_open_dates:
            if not booking_data.check_in_date or not booking_data.check_out_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Check-in and check-out dates are required for regular bookings",
                )

            if booking_data.check_in_date >= booking_data.check_out_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Check-out date must be after check-in date",
                )

            if not await self.check_availability(
                accommodation.id,
                booking_data.check_in_date,
                booking_data.check_out_date,
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Accommodation is not available for the selected dates",
                )

            # Calculate total amount based on nights and accommodation price
            nights = (booking_data.check_out_date - booking_data.check_in_date).days
            total_amount = accommodation.price_per_night * nights
        else:
            # For open dates bookings, no date validation needed
            total_amount = Decimal(0)

        db_booking = Booking(
            **booking_data.model_dump(),
            total_amount=total_amount,
            status=BookingStatus.PENDING,
        )

        self.db.add(db_booking)
        await self.db.commit()
        await self.db.refresh(db_booking)
        return db_booking

    async def create_open_dates(self, booking_data: BookingCreateOpenDates) -> Booking:
        """Create an open-dates booking"""
        regular_booking_data = BookingCreate(
            **booking_data.model_dump(),
            check_in_date=None,
            check_out_date=None,
            is_open_dates=True,
        )
        return await self.create(regular_booking_data)

    async def update(self, booking_id: int, booking_data: BookingUpdate) -> Booking:
        db_booking = await self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        # If updating dates for a non-open-dates booking, check availability
        if (
            booking_data.check_in_date is not None
            or booking_data.check_out_date is not None
        ) and not db_booking.is_open_dates:
            new_check_in = booking_data.check_in_date or db_booking.check_in_date
            new_check_out = booking_data.check_out_date or db_booking.check_out_date
            new_accommodation_id = (
                booking_data.accommodation_id or db_booking.accommodation_id
            )

            if new_check_in >= new_check_out:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Check-out date must be after check-in date",
                )

            if not await self.check_availability(
                new_accommodation_id, new_check_in, new_check_out, booking_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Accommodation is not available for the selected dates",
                )

        # Update fields
        update_data = booking_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_booking, field, value)

        # Recalculate total amount if dates or accommodation changed
        if (
            booking_data.check_in_date is not None
            or booking_data.check_out_date is not None
            or booking_data.accommodation_id is not None
        ) and not db_booking.is_open_dates:
            accommodation_stmt = select(Accommodation).where(
                Accommodation.id == db_booking.accommodation_id
            )
            accommodation_result = await self.db.execute(accommodation_stmt)
            accommodation = accommodation_result.scalar_one_or_none()
            if accommodation and db_booking.check_in_date and db_booking.check_out_date:
                nights = (db_booking.check_out_date - db_booking.check_in_date).days
                db_booking.total_amount = accommodation.price_per_night * nights

        await self.db.commit()
        await self.db.refresh(db_booking)
        return db_booking

    async def set_dates(self, booking_id: int, dates_data: BookingSetDates) -> Booking:
        """Set dates for an open-dates booking"""
        db_booking = await self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        if not db_booking.is_open_dates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only set dates for open-dates bookings",
            )

        if dates_data.check_in_date >= dates_data.check_out_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Check-out date must be after check-in date",
            )

        # Check availability
        if not await self.check_availability(
            db_booking.accommodation_id,
            dates_data.check_in_date,
            dates_data.check_out_date,
            booking_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Accommodation is not available for the selected dates",
            )

        # Update booking with dates
        db_booking.check_in_date = dates_data.check_in_date
        db_booking.check_out_date = dates_data.check_out_date
        db_booking.is_open_dates = False
        db_booking.status = BookingStatus.CONFIRMED

        # Calculate total amount
        accommodation_stmt = select(Accommodation).where(
            Accommodation.id == db_booking.accommodation_id
        )
        accommodation_result = await self.db.execute(accommodation_stmt)
        accommodation = accommodation_result.scalar_one_or_none()
        if accommodation:
            nights = (dates_data.check_out_date - dates_data.check_in_date).days
            db_booking.total_amount = accommodation.price_per_night * nights

        await self.db.commit()
        await self.db.refresh(db_booking)
        return db_booking

    async def check_in(self, booking_id: int, checkin_data: BookingCheckIn) -> Booking:
        """Process check-in for a booking"""
        db_booking = await self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        if db_booking.status != BookingStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only check-in confirmed bookings",
            )

        db_booking.status = BookingStatus.CHECKED_IN
        if checkin_data.actual_check_in:
            # Convert timezone-aware datetime to UTC timezone-naive datetime
            actual_check_in = checkin_data.actual_check_in
            if actual_check_in.tzinfo is not None:
                actual_check_in = actual_check_in.utctimetuple()
                actual_check_in = datetime(*actual_check_in[:6])
            db_booking.actual_check_in = actual_check_in
        else:
            db_booking.actual_check_in = datetime.utcnow()

        if checkin_data.comments:
            current_comments = db_booking.comments or ""
            db_booking.comments = (
                f"{current_comments}\nCheck-in: {checkin_data.comments}".strip()
            )

        await self.db.commit()
        await self.db.refresh(db_booking)
        return db_booking

    async def check_out(
        self, booking_id: int, checkout_data: BookingCheckOut
    ) -> Booking:
        """Process check-out for a booking"""
        db_booking = await self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        if db_booking.status != BookingStatus.CHECKED_IN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only check-out checked-in bookings",
            )

        db_booking.status = BookingStatus.CHECKED_OUT
        if checkout_data.actual_check_out:
            # Convert timezone-aware datetime to UTC timezone-naive datetime
            actual_check_out = checkout_data.actual_check_out
            if actual_check_out.tzinfo is not None:
                actual_check_out = actual_check_out.utctimetuple()
                actual_check_out = datetime(*actual_check_out[:6])
            db_booking.actual_check_out = actual_check_out
        else:
            db_booking.actual_check_out = datetime.utcnow()

        if checkout_data.comments:
            current_comments = db_booking.comments or ""
            db_booking.comments = (
                f"{current_comments}\nCheck-out: {checkout_data.comments}".strip()
            )

        await self.db.commit()
        await self.db.refresh(db_booking)
        return db_booking

    async def add_payment(
        self, booking_id: int, payment_data: BookingPayment
    ) -> Booking:
        """Add payment to a booking"""
        db_booking = await self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        # Add payment amount
        db_booking.paid_amount += payment_data.amount

        # Update payment status based on paid amount
        if db_booking.paid_amount >= db_booking.total_amount:
            db_booking.payment_status = PaymentStatus.PAID
        elif db_booking.paid_amount > 0:
            db_booking.payment_status = PaymentStatus.PARTIAL
        else:
            db_booking.payment_status = PaymentStatus.NOT_PAID

        # Add payment comment
        if payment_data.comments:
            current_comments = db_booking.comments or ""
            payment_note = f"Payment: +{payment_data.amount} - {payment_data.comments}"
            db_booking.comments = f"{current_comments}\n{payment_note}".strip()

        await self.db.commit()
        await self.db.refresh(db_booking)
        return db_booking

    async def cancel(self, booking_id: int, reason: Optional[str] = None) -> Booking:
        """Cancel a booking"""
        db_booking = await self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        if db_booking.status == BookingStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking is already cancelled",
            )

        if db_booking.status == BookingStatus.CHECKED_OUT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel completed bookings",
            )

        db_booking.status = BookingStatus.CANCELLED

        if reason:
            current_comments = db_booking.comments or ""
            db_booking.comments = f"{current_comments}\nCancelled: {reason}".strip()

        await self.db.commit()
        await self.db.refresh(db_booking)
        return db_booking

    async def delete(self, booking_id: int) -> bool:
        """Delete a booking (only if not checked-in or checked-out)"""
        db_booking = await self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        if db_booking.status in [BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete bookings that have been checked-in or completed",
            )

        self.db.delete(db_booking)
        await self.db.commit()
        return True

    async def get_with_details(self, booking_id: int) -> Optional[BookingWithDetails]:
        """Get booking with client and accommodation details"""
        booking = await self.get_by_id(booking_id)
        if not booking:
            return None

        booking_dict = booking.__dict__.copy()

        # Add client details
        if booking.client:
            booking_dict["client"] = {
                "id": booking.client.id,
                "first_name": booking.client.first_name,
                "last_name": booking.client.last_name,
                "phone": booking.client.phone,
                "email": booking.client.email,
            }

        # Add accommodation details
        if booking.accommodation:
            booking_dict["accommodation"] = {
                "id": booking.accommodation.id,
                "number": booking.accommodation.number,
                "type_name": booking.accommodation.type.name
                if booking.accommodation.type
                else None,
                "capacity": booking.accommodation.capacity,
                "price_per_night": float(booking.accommodation.price_per_night),
            }

        return BookingWithDetails.model_validate(booking_dict)

    # New methods for inventory and custom items integration
    async def create_with_items(self, booking_data: BookingCreateWithItems) -> Booking:
        """Create booking with inventory and custom items"""
        # Create base booking first
        base_booking_data = BookingCreate(
            client_id=booking_data.client_id,
            accommodation_id=booking_data.accommodation_id,
            check_in_date=booking_data.check_in_date,
            check_out_date=booking_data.check_out_date,
            is_open_dates=booking_data.is_open_dates,
            guests_count=booking_data.guests_count,
            comments=booking_data.comments,
        )

        booking = await self.create(base_booking_data)

        # Add inventory items
        if booking_data.inventory_items:
            await self._add_inventory_items(booking.id, booking_data.inventory_items)

        # Add custom items and recalculate total
        if booking_data.custom_items:
            await self._add_custom_items(booking.id, booking_data.custom_items)
            await self._recalculate_booking_total(booking.id)

        return await self.get_by_id(booking.id)

    async def create_open_dates_with_items(
        self, booking_data: BookingCreateOpenDatesWithItems
    ) -> Booking:
        """Create open-dates booking with inventory and custom items"""
        # Convert to regular booking data
        full_booking_data = BookingCreateWithItems(
            **booking_data.model_dump(),
            check_in_date=None,
            check_out_date=None,
            is_open_dates=True,
        )
        return await self.create_with_items(full_booking_data)

    async def _add_inventory_items(
        self, booking_id: int, inventory_items: list
    ) -> None:
        """Add inventory items to a booking"""
        inventory_service = InventoryService(self.db)

        for item_data in inventory_items:
            # Verify inventory item exists
            inventory_item = await inventory_service.get_inventory_item(
                item_data.inventory_item_id
            )
            if not inventory_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Inventory item {item_data.inventory_item_id} not found",
                )

            # Create booking inventory assignment
            booking_inventory = BookingInventory(
                booking_id=booking_id,
                inventory_item_id=item_data.inventory_item_id,
            )
            self.db.add(booking_inventory)

        await self.db.commit()

    async def _add_custom_items(self, booking_id: int, custom_items: list) -> None:
        """Add custom items to a booking"""
        custom_item_service = CustomItemService(self.db)

        for item_data in custom_items:
            await custom_item_service.create_booking_custom_item(booking_id, item_data)

    async def _recalculate_booking_total(self, booking_id: int) -> None:
        """Recalculate booking total including custom items"""
        booking = await self.get_by_id(booking_id)
        if not booking:
            return

        # Start with accommodation cost
        total = booking.total_amount

        # Add custom items cost
        custom_item_service = CustomItemService(self.db)
        custom_items_total = await custom_item_service.calculate_custom_items_total(
            booking_id
        )
        total += custom_items_total

        # Update booking total
        booking.total_amount = total
        await self.db.commit()

    async def get_with_items(self, booking_id: int) -> Optional[BookingWithItems]:
        """Get booking with inventory and custom items"""
        booking = await self.get_by_id(booking_id)
        if not booking:
            return None

        booking_dict = booking.__dict__.copy()

        # Add inventory items
        inventory_stmt = (
            select(BookingInventory)
            .options(
                selectinload(BookingInventory.inventory_item).selectinload(
                    InventoryItem.type
                )
            )
            .where(BookingInventory.booking_id == booking_id)
        )
        inventory_result = await self.db.execute(inventory_stmt)
        inventory_assignments = inventory_result.scalars().all()

        booking_dict["inventory_items"] = [
            {
                "id": assignment.id,
                "inventory_item_id": assignment.inventory_item_id,
                "inventory_item": {
                    "id": assignment.inventory_item.id,
                    "number": assignment.inventory_item.number,
                    "type_name": assignment.inventory_item.type.name
                    if assignment.inventory_item.type
                    else None,
                    "condition": assignment.inventory_item.condition.value,
                }
                if assignment.inventory_item
                else None,
            }
            for assignment in inventory_assignments
        ]

        # Add custom items
        custom_items_stmt = (
            select(BookingCustomItem)
            .options(selectinload(BookingCustomItem.custom_item))
            .where(BookingCustomItem.booking_id == booking_id)
        )
        custom_items_result = await self.db.execute(custom_items_stmt)
        custom_assignments = custom_items_result.scalars().all()

        booking_dict["custom_items"] = [
            {
                "id": assignment.id,
                "custom_item_id": assignment.custom_item_id,
                "quantity": assignment.quantity,
                "price_at_booking": float(assignment.price_at_booking),
                "custom_item": {
                    "id": assignment.custom_item.id,
                    "name": assignment.custom_item.name,
                    "description": assignment.custom_item.description,
                    "current_price": float(assignment.custom_item.price),
                }
                if assignment.custom_item
                else None,
            }
            for assignment in custom_assignments
        ]

        return BookingWithItems.model_validate(booking_dict)

    async def get_with_full_details(
        self, booking_id: int
    ) -> Optional[BookingWithFullDetails]:
        """Get booking with all details including client, accommodation, and items"""
        booking_with_details = await self.get_with_details(booking_id)
        booking_with_items = await self.get_with_items(booking_id)

        if not booking_with_details or not booking_with_items:
            return None

        # Combine both responses
        combined_dict = booking_with_details.model_dump()
        combined_dict["inventory_items"] = booking_with_items.inventory_items
        combined_dict["custom_items"] = booking_with_items.custom_items

        return BookingWithFullDetails.model_validate(combined_dict)

    async def add_inventory_item(self, booking_id: int, inventory_item_id: int) -> None:
        """Add an inventory item to an existing booking"""
        booking = await self.get_by_id(booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        inventory_service = InventoryService(self.db)
        inventory_item = await inventory_service.get_inventory_item(inventory_item_id)
        if not inventory_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inventory item not found",
            )

        # Check if item is already assigned to this booking
        existing_stmt = select(BookingInventory).where(
            and_(
                BookingInventory.booking_id == booking_id,
                BookingInventory.inventory_item_id == inventory_item_id,
            )
        )
        existing_result = await self.db.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inventory item already assigned to this booking",
            )

        booking_inventory = BookingInventory(
            booking_id=booking_id,
            inventory_item_id=inventory_item_id,
        )
        self.db.add(booking_inventory)
        await self.db.commit()

    async def remove_inventory_item(
        self, booking_id: int, inventory_item_id: int
    ) -> None:
        """Remove an inventory item from a booking"""
        stmt = select(BookingInventory).where(
            and_(
                BookingInventory.booking_id == booking_id,
                BookingInventory.inventory_item_id == inventory_item_id,
            )
        )
        result = await self.db.execute(stmt)
        booking_inventory = result.scalar_one_or_none()

        if not booking_inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not assigned to this booking",
            )

        await self.db.delete(booking_inventory)
        await self.db.commit()

    async def add_custom_item(
        self, booking_id: int, custom_item_id: int, quantity: int
    ) -> None:
        """Add a custom item to an existing booking"""
        booking = await self.get_by_id(booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        custom_item_service = CustomItemService(self.db)
        from app.schemas.custom_item import BookingCustomItemCreate

        custom_item_data = BookingCustomItemCreate(
            custom_item_id=custom_item_id, quantity=quantity
        )

        await custom_item_service.create_booking_custom_item(
            booking_id, custom_item_data
        )

        # Recalculate total
        await self._recalculate_booking_total(booking_id)

    async def remove_custom_item(self, booking_custom_item_id: int) -> None:
        """Remove a custom item from a booking"""
        custom_item_service = CustomItemService(self.db)
        booking_custom_item = await custom_item_service.get_booking_custom_item(
            booking_custom_item_id
        )

        if not booking_custom_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking custom item not found",
            )

        booking_id = booking_custom_item.booking_id
        await custom_item_service.delete_booking_custom_item(booking_custom_item_id)

        # Recalculate total
        await self._recalculate_booking_total(booking_id)
