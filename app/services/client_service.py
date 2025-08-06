from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ValidationError
from app.core.service_utils import ensure_exists, ensure_no_related_records
from app.models.booking import BookingStatus
from app.models.client import Client, ClientGroup
from app.schemas.client import (
    ClientCreate,
    ClientGroupCreate,
    ClientGroupUpdate,
    ClientUpdate,
    ClientWithStats,
)
from app.schemas.responses import PaginatedResponse
from app.schemas.search import ClientSearchRequest


class ClientGroupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[ClientGroup]:
        stmt = select(ClientGroup)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, group_id: int) -> Optional[ClientGroup]:
        stmt = select(ClientGroup).where(ClientGroup.id == group_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, group_data: ClientGroupCreate) -> ClientGroup:
        db_group = ClientGroup(**group_data.model_dump())
        self.db.add(db_group)
        await self.db.commit()
        await self.db.refresh(db_group)
        return db_group

    async def update(self, group_id: int, group_data: ClientGroupUpdate) -> ClientGroup:
        db_group = await self.get_by_id(group_id)
        db_group = ensure_exists(db_group, "Client group", group_id)

        update_data = group_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_group, field, value)

        await self.db.commit()
        await self.db.refresh(db_group)
        return db_group

    async def delete(self, group_id: int) -> bool:
        db_group = await self.get_by_id(group_id)
        db_group = ensure_exists(db_group, "Client group", group_id)

        # Check if group has clients
        clients_count_stmt = select(func.count(Client.id)).where(
            Client.group_id == group_id
        )
        clients_count_result = await self.db.execute(clients_count_stmt)
        clients_count = clients_count_result.scalar()

        ensure_no_related_records(clients_count or 0, "Client group", "clients")

        await self.db.delete(db_group)
        await self.db.commit()
        return True


class ClientService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Client]:
        stmt = select(Client).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, client_id: int) -> Optional[Client]:
        stmt = select(Client).where(Client.id == client_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search_clients(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> List[Client]:
        """Search clients by name, phone, or email"""
        if not query:
            return await self.get_all(skip, limit)

        search_filter = or_(
            func.lower(Client.first_name).contains(query.lower()),
            func.lower(Client.last_name).contains(query.lower()),
            Client.phone.contains(query),
            func.lower(Client.email).contains(query.lower()),
        )

        stmt = select(Client).where(search_filter).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_phone(self, phone: str) -> Optional[Client]:
        stmt = select(Client).where(Client.phone == phone)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Client]:
        stmt = select(Client).where(Client.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, client_data: ClientCreate) -> Client:
        # Check for duplicate phone/email if provided
        if client_data.phone and await self.get_by_phone(client_data.phone):
            raise ValidationError("Client with this phone number already exists")

        if client_data.email and await self.get_by_email(client_data.email):
            raise ValidationError("Client with this email already exists")

        db_client = Client(**client_data.model_dump())
        self.db.add(db_client)
        await self.db.commit()
        await self.db.refresh(db_client)
        return db_client

    async def update(self, client_id: int, client_data: ClientUpdate) -> Client:
        db_client = await self.get_by_id(client_id)
        db_client = ensure_exists(db_client, "Client", client_id)

        # Check for duplicate phone/email if being updated
        if client_data.phone and client_data.phone != db_client.phone:
            existing_client = await self.get_by_phone(client_data.phone)
            if existing_client and existing_client.id != client_id:
                raise ValidationError(
                    "Another client with this phone number already exists"
                )

        if client_data.email and client_data.email != db_client.email:
            existing_client = await self.get_by_email(client_data.email)
            if existing_client and existing_client.id != client_id:
                raise ValidationError("Another client with this email already exists")

        update_data = client_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_client, field, value)

        await self.db.commit()
        await self.db.refresh(db_client)
        return db_client

    async def delete(self, client_id: int) -> bool:
        db_client = await self.get_by_id(client_id)
        db_client = ensure_exists(db_client, "Client", client_id)

        await self.db.delete(db_client)
        await self.db.commit()
        return True

    async def get_client_stats(self, client_id: int) -> ClientWithStats:
        """Get client with basic statistics"""
        db_client = await self.get_by_id(client_id)
        db_client = ensure_exists(db_client, "Client", client_id)

        # For now, return zero stats since we don't have bookings yet
        # This will be updated in iteration 3 when booking system is implemented
        client_with_stats = ClientWithStats.model_validate(db_client)
        client_with_stats.visits_count = 0
        client_with_stats.total_spent = 0.0

        return client_with_stats

    # Enhanced search and filtering methods
    async def advanced_search(
        self, search_request: "ClientSearchRequest"
    ) -> "PaginatedResponse":
        """Perform advanced client search with multiple criteria and optimized performance."""
        from app.core.pagination import CursorPaginator, SortParams
        from app.core.query_builders import ClientQueryBuilder

        # Initialize query builder
        query_builder = ClientQueryBuilder(Client)
        filters = search_request.filters

        # Apply text search
        if filters.text_search and filters.text_search.query:
            query_builder.search_by_text(filters.text_search.query)

        # Apply specific field searches
        if filters.first_name:
            query_builder.where_text_contains(Client.first_name, filters.first_name)

        if filters.last_name:
            query_builder.where_text_contains(Client.last_name, filters.last_name)

        if filters.phone:
            query_builder.where_text_contains(Client.phone, filters.phone)

        if filters.email:
            query_builder.where_text_contains(Client.email, filters.email)

        # Apply group filters
        if filters.group_ids:
            query_builder.filter_by_group(filters.group_ids)

        if filters.has_group is not None:
            if filters.has_group:
                query_builder.where(Client.group_id.isnot(None))
            else:
                query_builder.where(Client.group_id.is_(None))

        # Apply rating filter
        if filters.rating_range:
            range_filter = filters.rating_range
            query_builder.filter_by_rating(
                range_filter.min_value, range_filter.max_value
            )

        # Apply date filters
        if filters.created_date_range:
            date_range = filters.created_date_range
            query_builder.where_date_range(
                Client.created_at, date_range.start_date, date_range.end_date
            )

        # Apply booking-related filters
        if filters.has_bookings is not None:
            query_builder.filter_by_has_bookings(filters.has_bookings)

        if filters.booking_status_filter:
            from app.models.booking import Booking

            status_values = [status.value for status in filters.booking_status_filter]
            booking_subquery = (
                select(Booking.client_id)
                .where(Booking.status.in_(status_values))
                .distinct()
            )

            if filters.has_bookings is False:
                query_builder.where(Client.id.notin_(booking_subquery))
            else:
                query_builder.where(Client.id.in_(booking_subquery))

        # Apply special filters
        if filters.car_numbers:
            # Search for any of the provided car numbers
            car_conditions = []
            for car_number in filters.car_numbers:
                car_conditions.append(Client.car_numbers.contains([car_number]))
            query_builder.where(or_(*car_conditions))

        if filters.has_photo is not None:
            if filters.has_photo:
                query_builder.where(Client.photo_url.isnot(None))
            else:
                query_builder.where(Client.photo_url.is_(None))

        if filters.comments_search:
            query_builder.where_text_contains(Client.comments, filters.comments_search)

        # Build the query
        base_query = query_builder.build()

        # Use cursor-based pagination for better performance
        paginator = CursorPaginator(Client, self.db)
        sort_params = SortParams(
            sort_by=search_request.sort.sort_by,
            sort_direction=search_request.sort.sort_direction,
        )

        return await paginator.paginate(
            base_query, search_request.pagination, sort_params, count_total=True
        )

    async def search_by_rating_range(
        self, min_rating: float, max_rating: float, skip: int = 0, limit: int = 100
    ) -> List[Client]:
        """Search clients by rating range."""
        stmt = (
            select(Client)
            .options(selectinload(Client.group))
            .where(and_(Client.rating >= min_rating, Client.rating <= max_rating))
            .order_by(Client.rating.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_clients_with_bookings(
        self,
        booking_statuses: Optional[List["BookingStatus"]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Client]:
        """Search clients who have bookings, optionally filtered by booking status."""
        from app.models.booking import Booking

        # Build subquery for clients with bookings
        booking_subquery = select(Booking.client_id).distinct()

        if booking_statuses:
            booking_subquery = booking_subquery.where(
                Booking.status.in_(booking_statuses)
            )

        stmt = (
            select(Client)
            .options(selectinload(Client.group))
            .where(Client.id.in_(booking_subquery))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_clients_by_group(
        self, group_ids: List[int], skip: int = 0, limit: int = 100
    ) -> List[Client]:
        """Search clients by group membership."""
        stmt = (
            select(Client)
            .options(selectinload(Client.group))
            .where(Client.group_id.in_(group_ids))
            .order_by(Client.group_id, Client.last_name, Client.first_name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_clients_by_car_number(
        self, car_number: str, skip: int = 0, limit: int = 100
    ) -> List[Client]:
        """Search clients by car number."""
        stmt = (
            select(Client)
            .options(selectinload(Client.group))
            .where(Client.car_numbers.contains([car_number]))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_clients_without_bookings(
        self, skip: int = 0, limit: int = 100
    ) -> List[Client]:
        """Get clients who have never made a booking."""
        from app.models.booking import Booking

        # Subquery for clients with bookings
        clients_with_bookings = select(Booking.client_id).distinct()

        stmt = (
            select(Client)
            .options(selectinload(Client.group))
            .where(Client.id.notin_(clients_with_bookings))
            .order_by(Client.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_top_clients_by_spending(
        self, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top clients by total spending."""
        from app.models.booking import Booking, BookingStatus

        stmt = (
            select(
                Client.id,
                Client.first_name,
                Client.last_name,
                Client.email,
                Client.phone,
                Client.rating,
                func.sum(Booking.total_amount).label("total_spent"),
                func.count(Booking.id).label("booking_count"),
            )
            .join(Booking, Client.id == Booking.client_id)
            .where(
                Booking.status.in_(
                    [
                        BookingStatus.CONFIRMED,
                        BookingStatus.CHECKED_IN,
                        BookingStatus.CHECKED_OUT,
                    ]
                )
            )
            .group_by(Client.id)
            .order_by(func.sum(Booking.total_amount).desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return [
            {
                "client_id": row.id,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "email": row.email,
                "phone": row.phone,
                "rating": float(row.rating) if row.rating else 0.0,
                "total_spent": float(row.total_spent),
                "booking_count": row.booking_count,
            }
            for row in result.all()
        ]

    async def get_client_statistics_detailed(self, client_id: int) -> Dict[str, Any]:
        """Get detailed statistics for a specific client."""
        from app.models.booking import Booking, BookingStatus

        client = await self.get_by_id(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Get booking statistics
        booking_stats_stmt = select(
            func.count(Booking.id).label("total_bookings"),
            func.sum(Booking.total_amount).label("total_spent"),
            func.sum(Booking.paid_amount).label("total_paid"),
            func.avg(Booking.total_amount).label("average_booking_value"),
            func.min(Booking.created_at).label("first_booking_date"),
            func.max(Booking.created_at).label("last_booking_date"),
        ).where(
            and_(
                Booking.client_id == client_id,
                Booking.status.in_(
                    [
                        BookingStatus.CONFIRMED,
                        BookingStatus.CHECKED_IN,
                        BookingStatus.CHECKED_OUT,
                    ]
                ),
            )
        )

        booking_result = await self.db.execute(booking_stats_stmt)
        booking_stats = booking_result.first()

        # Get booking status breakdown
        status_breakdown_stmt = (
            select(Booking.status, func.count(Booking.id).label("count"))
            .where(Booking.client_id == client_id)
            .group_by(Booking.status)
        )

        status_result = await self.db.execute(status_breakdown_stmt)
        status_breakdown = {row.status.value: row.count for row in status_result.all()}

        # Get payment status breakdown
        payment_breakdown_stmt = (
            select(Booking.payment_status, func.count(Booking.id).label("count"))
            .where(Booking.client_id == client_id)
            .group_by(Booking.payment_status)
        )

        payment_result = await self.db.execute(payment_breakdown_stmt)
        payment_breakdown = {
            row.payment_status.value: row.count for row in payment_result.all()
        }

        return {
            "client_id": client_id,
            "client_info": {
                "first_name": client.first_name,
                "last_name": client.last_name,
                "email": client.email,
                "phone": client.phone,
                "rating": float(client.rating) if client.rating else 0.0,
                "created_at": client.created_at,
                "group": client.group.name if client.group else None,
            },
            "booking_statistics": {
                "total_bookings": booking_stats.total_bookings or 0,
                "total_spent": float(booking_stats.total_spent or 0),
                "total_paid": float(booking_stats.total_paid or 0),
                "outstanding_amount": float(
                    (booking_stats.total_spent or 0) - (booking_stats.total_paid or 0)
                ),
                "average_booking_value": float(
                    booking_stats.average_booking_value or 0
                ),
                "first_booking_date": booking_stats.first_booking_date,
                "last_booking_date": booking_stats.last_booking_date,
            },
            "status_breakdown": status_breakdown,
            "payment_breakdown": payment_breakdown,
        }

    async def get_client_booking_summary(
        self, client_id: int, limit: int = 10
    ) -> Dict[str, Any]:
        """Get a summary of recent bookings for a client."""
        from app.models.accommodation import Accommodation
        from app.models.booking import Booking

        # Get recent bookings
        recent_bookings_stmt = (
            select(Booking)
            .options(
                selectinload(Booking.accommodation).selectinload(Accommodation.type)
            )
            .where(Booking.client_id == client_id)
            .order_by(Booking.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(recent_bookings_stmt)
        recent_bookings = result.scalars().all()

        return {
            "client_id": client_id,
            "recent_bookings": [
                {
                    "booking_id": booking.id,
                    "status": booking.status.value,
                    "payment_status": booking.payment_status.value,
                    "check_in_date": booking.check_in_date,
                    "check_out_date": booking.check_out_date,
                    "is_open_dates": booking.is_open_dates,
                    "guests_count": booking.guests_count,
                    "total_amount": float(booking.total_amount),
                    "paid_amount": float(booking.paid_amount),
                    "accommodation": {
                        "id": booking.accommodation.id,
                        "number": booking.accommodation.number,
                        "type_name": booking.accommodation.type.name
                        if booking.accommodation.type
                        else None,
                    },
                    "created_at": booking.created_at,
                }
                for booking in recent_bookings
            ],
        }
