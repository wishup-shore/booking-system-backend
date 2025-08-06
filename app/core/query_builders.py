from datetime import date, datetime
from typing import Any, List, Optional, Union

from sqlalchemy import Select, and_, asc, desc, func, or_, select
from sqlalchemy.orm import selectinload


class BaseQueryBuilder:
    """Base query builder with common filtering and sorting capabilities."""

    def __init__(self, model_class):
        self.model_class = model_class
        self.query = select(model_class)
        self.filters = []
        self.joins = []
        self.order_by_clauses = []
        self._includes = []

    def where(self, condition):
        """Add a WHERE condition to the query."""
        self.filters.append(condition)
        return self

    def where_in(self, field, values: List[Any]):
        """Add WHERE field IN (values) condition."""
        if values:
            self.filters.append(field.in_(values))
        return self

    def where_text_contains(self, field, text: str, case_insensitive: bool = True):
        """Add text search condition with optional case insensitivity."""
        if text:
            if case_insensitive:
                self.filters.append(func.lower(field).contains(text.lower()))
            else:
                self.filters.append(field.contains(text))
        return self

    def where_text_search(self, fields: List, query: str):
        """Add multi-field text search using OR conditions."""
        if query and fields:
            search_conditions = []
            for field in fields:
                search_conditions.append(func.lower(field).contains(query.lower()))
            self.filters.append(or_(*search_conditions))
        return self

    def where_date_range(
        self, field, start_date: Optional[date], end_date: Optional[date]
    ):
        """Add date range filtering."""
        if start_date:
            self.filters.append(field >= start_date)
        if end_date:
            self.filters.append(field <= end_date)
        return self

    def where_datetime_range(
        self,
        field,
        start_datetime: Optional[datetime],
        end_datetime: Optional[datetime],
    ):
        """Add datetime range filtering."""
        if start_datetime:
            self.filters.append(field >= start_datetime)
        if end_datetime:
            self.filters.append(field <= end_datetime)
        return self

    def where_number_range(
        self,
        field,
        min_value: Optional[Union[int, float]],
        max_value: Optional[Union[int, float]],
    ):
        """Add numeric range filtering."""
        if min_value is not None:
            self.filters.append(field >= min_value)
        if max_value is not None:
            self.filters.append(field <= max_value)
        return self

    def include(self, *relationships):
        """Add relationships to eager load."""
        for relationship in relationships:
            self._includes.append(selectinload(relationship))
        return self

    def order_by(self, field, direction: str = "asc"):
        """Add ORDER BY clause."""
        if direction.lower() == "desc":
            self.order_by_clauses.append(desc(field))
        else:
            self.order_by_clauses.append(asc(field))
        return self

    def order_by_relevance(self, search_text: str, text_fields: List):
        """Add relevance-based ordering for text search."""
        if search_text and text_fields:
            # Simple relevance scoring based on exact matches vs partial matches
            relevance_score = func.coalesce(
                sum(
                    [
                        func.case(
                            (func.lower(field) == search_text.lower(), 10),
                            (func.lower(field).contains(search_text.lower()), 5),
                            else_=0,
                        )
                        for field in text_fields
                    ]
                ),
                0,
            )
            self.order_by_clauses.append(desc(relevance_score))
        return self

    def paginate(self, skip: int = 0, limit: int = 100):
        """Add pagination to the query."""
        self.query = self.query.offset(skip).limit(limit)
        return self

    def build(self) -> Select:
        """Build the final query with all conditions applied."""
        if self._includes:
            self.query = self.query.options(*self._includes)

        if self.filters:
            self.query = self.query.where(and_(*self.filters))

        if self.order_by_clauses:
            self.query = self.query.order_by(*self.order_by_clauses)

        return self.query


class BookingQueryBuilder(BaseQueryBuilder):
    """Specialized query builder for booking searches."""

    def __init__(self, model_class):
        super().__init__(model_class)
        # Default includes for booking queries
        self.include(model_class.client, model_class.accommodation)

    def filter_by_status(self, statuses: List[str]):
        """Filter by booking status(es)."""
        if statuses:
            from app.models.booking import BookingStatus

            enum_statuses = [BookingStatus(status) for status in statuses]
            return self.where_in(self.model_class.status, enum_statuses)
        return self

    def filter_by_payment_status(self, payment_statuses: List[str]):
        """Filter by payment status(es)."""
        if payment_statuses:
            from app.models.booking import PaymentStatus

            enum_statuses = [PaymentStatus(status) for status in payment_statuses]
            return self.where_in(self.model_class.payment_status, enum_statuses)
        return self

    def filter_by_dates(self, start_date: Optional[date], end_date: Optional[date]):
        """Filter by check-in/check-out date range."""
        return self.where_date_range(
            self.model_class.check_in_date, start_date, end_date
        )

    def filter_by_open_dates(self, is_open_dates: Optional[bool]):
        """Filter by open dates bookings."""
        if is_open_dates is not None:
            return self.where(self.model_class.is_open_dates == is_open_dates)
        return self

    def filter_by_client_name(self, client_name: str):
        """Filter by client name (first or last name)."""
        if client_name:
            from app.models.client import Client

            return self.where(
                or_(
                    func.lower(Client.first_name).contains(client_name.lower()),
                    func.lower(Client.last_name).contains(client_name.lower()),
                    func.concat(
                        func.lower(Client.first_name), " ", func.lower(Client.last_name)
                    ).contains(client_name.lower()),
                )
            )
        return self

    def filter_by_accommodation_type(self, accommodation_type_ids: List[int]):
        """Filter by accommodation type."""
        if accommodation_type_ids:
            from app.models.accommodation import Accommodation

            return self.where_in(Accommodation.type_id, accommodation_type_ids)
        return self

    def filter_by_guest_count(
        self, min_guests: Optional[int], max_guests: Optional[int]
    ):
        """Filter by guest count range."""
        return self.where_number_range(
            self.model_class.guests_count, min_guests, max_guests
        )

    def filter_by_amount_range(
        self, min_amount: Optional[float], max_amount: Optional[float]
    ):
        """Filter by total amount range."""
        return self.where_number_range(
            self.model_class.total_amount, min_amount, max_amount
        )


class ClientQueryBuilder(BaseQueryBuilder):
    """Specialized query builder for client searches."""

    def __init__(self, model_class):
        super().__init__(model_class)
        # Default includes for client queries
        self.include(model_class.group)

    def search_by_text(self, search_text: str):
        """Search clients by name, phone, or email."""
        if search_text:
            return self.where_text_search(
                [
                    self.model_class.first_name,
                    self.model_class.last_name,
                    self.model_class.phone,
                    self.model_class.email,
                ],
                search_text,
            )
        return self

    def filter_by_rating(
        self, min_rating: Optional[float], max_rating: Optional[float]
    ):
        """Filter by client rating range."""
        return self.where_number_range(self.model_class.rating, min_rating, max_rating)

    def filter_by_group(self, group_ids: List[int]):
        """Filter by client group membership."""
        if group_ids:
            return self.where_in(self.model_class.group_id, group_ids)
        return self

    def filter_by_has_bookings(self, has_bookings: Optional[bool]):
        """Filter clients who have/don't have bookings."""
        if has_bookings is not None:
            from app.models.booking import Booking

            if has_bookings:
                return self.where(
                    self.model_class.id.in_(select(Booking.client_id).distinct())
                )
            else:
                return self.where(
                    self.model_class.id.notin_(select(Booking.client_id).distinct())
                )
        return self


class AccommodationQueryBuilder(BaseQueryBuilder):
    """Specialized query builder for accommodation searches."""

    def __init__(self, model_class):
        super().__init__(model_class)
        # Default includes for accommodation queries
        self.include(model_class.type)

    def filter_by_type(self, type_ids: List[int]):
        """Filter by accommodation type."""
        if type_ids:
            return self.where_in(self.model_class.type_id, type_ids)
        return self

    def filter_by_status(self, statuses: List[str]):
        """Filter by accommodation status."""
        if statuses:
            from app.models.accommodation import AccommodationStatus

            enum_statuses = [AccommodationStatus(status) for status in statuses]
            return self.where_in(self.model_class.status, enum_statuses)
        return self

    def filter_by_condition(self, conditions: List[str]):
        """Filter by accommodation condition."""
        if conditions:
            from app.models.accommodation import AccommodationCondition

            enum_conditions = [
                AccommodationCondition(condition) for condition in conditions
            ]
            return self.where_in(self.model_class.condition, enum_conditions)
        return self

    def filter_by_capacity(
        self, min_capacity: Optional[int], max_capacity: Optional[int]
    ):
        """Filter by capacity range."""
        return self.where_number_range(
            self.model_class.capacity, min_capacity, max_capacity
        )

    def filter_by_price_range(
        self, min_price: Optional[float], max_price: Optional[float]
    ):
        """Filter by price per night range."""
        return self.where_number_range(
            self.model_class.price_per_night, min_price, max_price
        )

    def filter_available_for_dates(self, start_date: date, end_date: date):
        """Filter accommodations available for specific date range."""
        from app.models.booking import Booking, BookingStatus

        # Exclude accommodations with conflicting bookings
        conflicting_bookings = (
            select(Booking.accommodation_id)
            .where(
                and_(
                    Booking.status.in_(
                        [BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]
                    ),
                    or_(
                        and_(
                            Booking.check_in_date <= start_date,
                            Booking.check_out_date > start_date,
                        ),
                        and_(
                            Booking.check_in_date < end_date,
                            Booking.check_out_date >= end_date,
                        ),
                        and_(
                            Booking.check_in_date >= start_date,
                            Booking.check_out_date <= end_date,
                        ),
                    ),
                )
            )
            .distinct()
        )

        return self.where(self.model_class.id.notin_(conflicting_bookings))
