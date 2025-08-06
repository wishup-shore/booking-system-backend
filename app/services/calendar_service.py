from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accommodation import Accommodation
from app.models.booking import Booking, BookingStatus
from app.schemas.booking import CalendarEvent, CalendarOccupancy


class CalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_occupancy_for_month(
        self, year: int, month: int
    ) -> List[CalendarOccupancy]:
        """Get occupancy data for a specific month"""
        # Create date range for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        return await self.get_occupancy_for_date_range(start_date, end_date)

    async def get_occupancy_for_date_range(
        self, start_date: date, end_date: date
    ) -> List[CalendarOccupancy]:
        """Get occupancy data for a date range"""
        # Get all accommodations
        accommodations_stmt = select(Accommodation).options(
            selectinload(Accommodation.type)
        )
        accommodations_result = await self.db.execute(accommodations_stmt)
        accommodations = accommodations_result.scalars().all()

        # Get all bookings in the date range
        bookings_stmt = (
            select(Booking)
            .options(selectinload(Booking.client), selectinload(Booking.accommodation))
            .where(
                and_(
                    not Booking.is_open_dates,  # Only bookings with confirmed dates
                    Booking.status.in_(
                        [
                            BookingStatus.CONFIRMED,
                            BookingStatus.CHECKED_IN,
                            BookingStatus.CHECKED_OUT,
                        ]
                    ),
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
        bookings_result = await self.db.execute(bookings_stmt)
        bookings = bookings_result.scalars().all()

        # Build occupancy data for each date
        occupancy_data = []
        current_date = start_date

        while current_date <= end_date:
            # Find accommodations occupied on this date
            accommodations_for_date = []

            for accommodation in accommodations:
                # Check if this accommodation is booked on this date
                booking_for_date = None
                for booking in bookings:
                    if (
                        booking.accommodation_id == accommodation.id
                        and booking.check_in_date
                        <= current_date
                        < booking.check_out_date
                    ):
                        booking_for_date = booking
                        break

                accommodation_data = {
                    "id": accommodation.id,
                    "number": accommodation.number,
                    "type_name": accommodation.type.name
                    if accommodation.type
                    else "Unknown",
                    "capacity": accommodation.capacity,
                    "status": accommodation.status.value,
                    "is_occupied": booking_for_date is not None,
                    "booking": None,
                }

                if booking_for_date:
                    accommodation_data["booking"] = {
                        "id": booking_for_date.id,
                        "client_name": f"{booking_for_date.client.first_name} {booking_for_date.client.last_name}",
                        "client_phone": booking_for_date.client.phone,
                        "guests_count": booking_for_date.guests_count,
                        "status": booking_for_date.status.value,
                        "payment_status": booking_for_date.payment_status.value,
                        "check_in_date": booking_for_date.check_in_date.isoformat(),
                        "check_out_date": booking_for_date.check_out_date.isoformat(),
                    }

                accommodations_for_date.append(accommodation_data)

            occupancy_data.append(
                CalendarOccupancy(
                    date=current_date, accommodations=accommodations_for_date
                )
            )

            current_date += timedelta(days=1)

        return occupancy_data

    async def get_calendar_events(
        self, start_date: date, end_date: date
    ) -> List[CalendarEvent]:
        """Get calendar events (bookings) for calendar display"""
        bookings_stmt = (
            select(Booking)
            .options(
                selectinload(Booking.client),
                selectinload(Booking.accommodation).selectinload(Accommodation.type),
            )
            .where(
                and_(
                    not Booking.is_open_dates,  # Only bookings with confirmed dates
                    Booking.status.in_(
                        [
                            BookingStatus.CONFIRMED,
                            BookingStatus.CHECKED_IN,
                            BookingStatus.CHECKED_OUT,
                        ]
                    ),
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
        bookings_result = await self.db.execute(bookings_stmt)
        bookings = bookings_result.scalars().all()

        events = []
        for booking in bookings:
            event = CalendarEvent(
                id=booking.id,
                title=f"{booking.client.first_name} {booking.client.last_name} ({booking.guests_count})",
                start=booking.check_in_date,
                end=booking.check_out_date,
                accommodation_id=booking.accommodation_id,
                accommodation_number=booking.accommodation.number,
                client_name=f"{booking.client.first_name} {booking.client.last_name}",
                status=booking.status,
                is_open_dates=booking.is_open_dates,
            )
            events.append(event)

        return events

    async def check_accommodation_availability(
        self,
        accommodation_id: int,
        start_date: date,
        end_date: date,
        exclude_booking_id: Optional[int] = None,
    ) -> bool:
        """Check if a specific accommodation is available for given dates"""
        conditions = [
            Booking.accommodation_id == accommodation_id,
            not Booking.is_open_dates,  # Only bookings with confirmed dates
            Booking.status.in_(
                [
                    BookingStatus.PENDING,
                    BookingStatus.CONFIRMED,
                    BookingStatus.CHECKED_IN,
                ]
            ),
            and_(
                Booking.check_in_date < end_date,
                Booking.check_out_date > start_date,
            ),
        ]

        if exclude_booking_id:
            conditions.append(Booking.id != exclude_booking_id)

        stmt = select(func.count(Booking.id)).where(and_(*conditions))
        result = await self.db.execute(stmt)
        count = result.scalar()
        return count == 0

    async def get_available_accommodations(
        self, start_date: date, end_date: date, capacity_needed: Optional[int] = None
    ) -> List[Accommodation]:
        """Get all accommodations available for given dates"""
        # Get all accommodations that meet capacity requirements
        accommodations_stmt = select(Accommodation).options(
            selectinload(Accommodation.type)
        )

        if capacity_needed:
            accommodations_stmt = accommodations_stmt.where(
                Accommodation.capacity >= capacity_needed
            )

        accommodations_result = await self.db.execute(accommodations_stmt)
        all_accommodations = accommodations_result.scalars().all()

        # Filter out accommodations that are booked during the requested period
        available_accommodations = []
        for accommodation in all_accommodations:
            if await self.check_accommodation_availability(
                accommodation.id, start_date, end_date
            ):
                available_accommodations.append(accommodation)

        return available_accommodations

    async def get_occupancy_statistics(self, start_date: date, end_date: date) -> Dict:
        """Get occupancy statistics for a date range"""
        total_accommodations_stmt = select(func.count(Accommodation.id))
        total_accommodations_result = await self.db.execute(total_accommodations_stmt)
        total_accommodations = total_accommodations_result.scalar()

        if total_accommodations == 0:
            return {
                "total_accommodations": 0,
                "occupied_nights": 0,
                "available_nights": 0,
                "occupancy_rate": 0.0,
                "total_revenue": 0.0,
                "average_daily_rate": 0.0,
                "revenue_per_available_room": 0.0,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
            }

        # Calculate total possible nights
        total_days = (end_date - start_date).days + 1
        total_nights = total_accommodations * total_days

        # Get bookings in the date range
        bookings_stmt = (
            select(Booking)
            .options(selectinload(Booking.accommodation))
            .where(
                and_(
                    not Booking.is_open_dates,
                    Booking.status.in_(
                        [
                            BookingStatus.CONFIRMED,
                            BookingStatus.CHECKED_IN,
                            BookingStatus.CHECKED_OUT,
                        ]
                    ),
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
        bookings_result = await self.db.execute(bookings_stmt)
        bookings = bookings_result.scalars().all()

        occupied_nights = 0
        total_revenue = 0.0

        for booking in bookings:
            # Calculate overlap with requested date range
            booking_start = max(booking.check_in_date, start_date)
            booking_end = min(booking.check_out_date, end_date)

            if booking_start < booking_end:
                nights = (booking_end - booking_start).days
                occupied_nights += nights

                # Calculate revenue for this booking's overlap period
                if booking.accommodation and booking.accommodation.price_per_night:
                    total_revenue += (
                        float(booking.accommodation.price_per_night) * nights
                    )

        occupancy_rate = (
            (occupied_nights / total_nights * 100) if total_nights > 0 else 0.0
        )

        # Calculate additional metrics
        available_nights = total_nights
        average_daily_rate = (
            total_revenue / occupied_nights if occupied_nights > 0 else 0.0
        )
        revenue_per_available_room = (
            total_revenue / available_nights if available_nights > 0 else 0.0
        )

        return {
            "total_accommodations": total_accommodations,
            "occupied_nights": occupied_nights,
            "available_nights": available_nights,
            "occupancy_rate": round(occupancy_rate, 2),
            "total_revenue": round(total_revenue, 2),
            "average_daily_rate": round(average_daily_rate, 2),
            "revenue_per_available_room": round(revenue_per_available_room, 2),
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        }

    async def get_accommodation_schedule(
        self, accommodation_id: int, start_date: date, end_date: date
    ) -> List[Dict]:
        """Get detailed schedule for a specific accommodation"""
        accommodation_stmt = (
            select(Accommodation)
            .options(selectinload(Accommodation.type))
            .where(Accommodation.id == accommodation_id)
        )
        accommodation_result = await self.db.execute(accommodation_stmt)
        accommodation = accommodation_result.scalar_one_or_none()

        if not accommodation:
            return []

        bookings_stmt = (
            select(Booking)
            .options(selectinload(Booking.client))
            .where(
                and_(
                    Booking.accommodation_id == accommodation_id,
                    not Booking.is_open_dates,
                    Booking.status.in_(
                        [
                            BookingStatus.CONFIRMED,
                            BookingStatus.CHECKED_IN,
                            BookingStatus.CHECKED_OUT,
                        ]
                    ),
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
            .order_by(Booking.check_in_date)
        )
        bookings_result = await self.db.execute(bookings_stmt)
        bookings = bookings_result.scalars().all()

        schedule = []
        for booking in bookings:
            schedule_item = {
                "booking_id": booking.id,
                "check_in_date": booking.check_in_date.isoformat(),
                "check_out_date": booking.check_out_date.isoformat(),
                "client": {
                    "id": booking.client.id,
                    "name": f"{booking.client.first_name} {booking.client.last_name}",
                    "phone": booking.client.phone,
                },
                "guests_count": booking.guests_count,
                "status": booking.status.value,
                "payment_status": booking.payment_status.value,
                "total_amount": float(booking.total_amount),
                "paid_amount": float(booking.paid_amount),
            }
            schedule.append(schedule_item)

        return schedule

    async def find_next_available_slot(
        self, accommodation_id: int, after_date: date, min_nights: int = 1
    ) -> Optional[Tuple[date, date]]:
        """Find the next available slot for an accommodation after a given date"""
        # Get bookings for this accommodation after the given date
        bookings_stmt = (
            select(Booking)
            .where(
                and_(
                    Booking.accommodation_id == accommodation_id,
                    not Booking.is_open_dates,
                    Booking.status.in_(
                        [BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]
                    ),
                    Booking.check_in_date >= after_date,
                )
            )
            .order_by(Booking.check_in_date)
        )
        bookings_result = await self.db.execute(bookings_stmt)
        bookings = bookings_result.scalars().all()

        current_date = after_date

        for booking in bookings:
            # Check if there's enough space before this booking
            available_days = (booking.check_in_date - current_date).days
            if available_days >= min_nights:
                return current_date, booking.check_in_date

            # Move to the end of this booking
            current_date = booking.check_out_date

        # If we get here, there's availability after all bookings
        return current_date, current_date + timedelta(days=min_nights)
