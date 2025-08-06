import base64
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field, validator
from sqlalchemy import Select, asc, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class CursorInfo(BaseModel):
    """Information about cursor pagination state."""

    field: str
    value: Any
    direction: str = "asc"  # asc or desc


class PaginationParams(BaseModel):
    """Cursor-based pagination parameters."""

    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    limit: int = Field(
        default=50, ge=1, le=100, description="Number of items to return"
    )

    @validator("cursor")
    def validate_cursor(cls, v):
        if v is not None:
            try:
                decode_cursor(v)
            except Exception:
                raise ValueError("Invalid cursor format")
        return v


class SortParams(BaseModel):
    """Sorting parameters for queries."""

    sort_by: str = Field(default="id", description="Field to sort by")
    sort_direction: str = Field(default="asc", description="Sort direction (asc/desc)")

    @validator("sort_direction")
    def validate_sort_direction(cls, v):
        if v.lower() not in ["asc", "desc"]:
            raise ValueError("Sort direction must be 'asc' or 'desc'")
        return v.lower()


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response with cursor-based pagination."""

    items: List[T]
    pagination: Dict[str, Any]

    @classmethod
    def create(
        cls,
        items: List[T],
        has_next: bool,
        has_previous: bool,
        total_count: Optional[int] = None,
        next_cursor: Optional[str] = None,
        previous_cursor: Optional[str] = None,
    ):
        return cls(
            items=items,
            pagination={
                "has_next": has_next,
                "has_previous": has_previous,
                "total_count": total_count,
                "next_cursor": next_cursor,
                "previous_cursor": previous_cursor,
                "count": len(items),
            },
        )


class SearchMetadata(BaseModel):
    """Metadata for search results."""

    query: str
    total_results: int
    search_time_ms: float
    filters_applied: Dict[str, Any]
    sort_by: str
    sort_direction: str


class SearchResponse(BaseModel, Generic[T]):
    """Search response with metadata and pagination."""

    items: List[T]
    pagination: Dict[str, Any]
    metadata: SearchMetadata


def encode_cursor(cursor_info: CursorInfo) -> str:
    """Encode cursor information to base64 string."""
    # Handle special types that aren't JSON serializable
    value = cursor_info.value
    if isinstance(value, (datetime, date)):
        value = value.isoformat()
    elif isinstance(value, Decimal):
        value = float(value)

    cursor_data = {
        "field": cursor_info.field,
        "value": value,
        "direction": cursor_info.direction,
    }

    json_str = json.dumps(cursor_data, sort_keys=True)
    return base64.b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> CursorInfo:
    """Decode base64 cursor string to cursor information."""
    try:
        json_str = base64.b64decode(cursor.encode()).decode()
        cursor_data = json.loads(json_str)
        return CursorInfo(**cursor_data)
    except Exception as e:
        raise ValueError(f"Invalid cursor format: {e}")


class CursorPaginator:
    """Cursor-based paginator for efficient pagination."""

    def __init__(self, model_class, session: AsyncSession):
        self.model_class = model_class
        self.session = session

    def _get_cursor_field(self, field_name: str):
        """Get the SQLAlchemy column for cursor field."""
        return getattr(self.model_class, field_name)

    def _apply_cursor_filter(self, query: Select, cursor_info: CursorInfo):
        """Apply cursor-based filtering to query."""
        cursor_field = self._get_cursor_field(cursor_info.field)

        # Convert string values back to appropriate types
        value = cursor_info.value
        if hasattr(cursor_field.type, "python_type"):
            if cursor_field.type.python_type == datetime:
                value = datetime.fromisoformat(value)
            elif cursor_field.type.python_type == date:
                value = date.fromisoformat(value)
            elif cursor_field.type.python_type == Decimal:
                value = Decimal(str(value))

        if cursor_info.direction == "asc":
            return query.where(cursor_field > value)
        else:
            return query.where(cursor_field < value)

    def _apply_sorting(self, query: Select, sort_params: SortParams):
        """Apply sorting to query."""
        sort_field = self._get_cursor_field(sort_params.sort_by)

        if sort_params.sort_direction == "desc":
            return query.order_by(desc(sort_field))
        else:
            return query.order_by(asc(sort_field))

    async def paginate(
        self,
        query: Select,
        pagination: PaginationParams,
        sort_params: SortParams,
        count_total: bool = False,
    ) -> PaginatedResponse:
        """Paginate query results using cursor-based pagination."""

        # Apply sorting
        sorted_query = self._apply_sorting(query, sort_params)

        # Apply cursor filter if provided
        if pagination.cursor:
            cursor_info = decode_cursor(pagination.cursor)
            sorted_query = self._apply_cursor_filter(sorted_query, cursor_info)

        # Fetch one extra item to determine if there's a next page
        fetch_limit = pagination.limit + 1
        sorted_query = sorted_query.limit(fetch_limit)

        # Execute query
        result = await self.session.execute(sorted_query)
        items = list(result.scalars().all())

        # Determine pagination state
        has_next = len(items) > pagination.limit
        if has_next:
            items = items[:-1]  # Remove the extra item

        has_previous = pagination.cursor is not None

        # Generate next cursor
        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            cursor_value = getattr(last_item, sort_params.sort_by)
            next_cursor = encode_cursor(
                CursorInfo(
                    field=sort_params.sort_by,
                    value=cursor_value,
                    direction=sort_params.sort_direction,
                )
            )

        # Generate previous cursor (simplified - in production might want more sophisticated approach)
        previous_cursor = None
        if has_previous and items:
            first_item = items[0]
            cursor_value = getattr(first_item, sort_params.sort_by)
            # Reverse direction for previous cursor
            prev_direction = "desc" if sort_params.sort_direction == "asc" else "asc"
            previous_cursor = encode_cursor(
                CursorInfo(
                    field=sort_params.sort_by,
                    value=cursor_value,
                    direction=prev_direction,
                )
            )

        # Get total count if requested
        total_count = None
        if count_total:
            count_query = query.with_only_columns(func.count())
            count_result = await self.session.execute(count_query)
            total_count = count_result.scalar()

        return PaginatedResponse.create(
            items=items,
            has_next=has_next,
            has_previous=has_previous,
            total_count=total_count,
            next_cursor=next_cursor,
            previous_cursor=previous_cursor,
        )


class OffsetPagination(BaseModel):
    """Traditional offset-based pagination (for backwards compatibility)."""

    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(
        default=50, ge=1, le=100, description="Number of items to return"
    )


class OffsetPaginatedResponse(BaseModel, Generic[T]):
    """Traditional paginated response with offset-based pagination."""

    items: List[T]
    pagination: Dict[str, Any]

    @classmethod
    def create(cls, items: List[T], total_count: int, skip: int, limit: int):
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1

        return cls(
            items=items,
            pagination={
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": current_page,
                "per_page": limit,
                "has_next": skip + limit < total_count,
                "has_previous": skip > 0,
                "count": len(items),
            },
        )


class FilterParams(BaseModel):
    """Base class for filter parameters."""

    pass


class DateRangeFilter(BaseModel):
    """Date range filter parameters."""

    start_date: Optional[date] = Field(None, description="Start date (inclusive)")
    end_date: Optional[date] = Field(None, description="End date (inclusive)")

    @validator("end_date")
    def validate_date_range(cls, v, values):
        if v and "start_date" in values and values["start_date"]:
            if v < values["start_date"]:
                raise ValueError("End date must be after start date")
        return v


class NumericRangeFilter(BaseModel):
    """Numeric range filter parameters."""

    min_value: Optional[Union[int, float]] = Field(
        None, description="Minimum value (inclusive)"
    )
    max_value: Optional[Union[int, float]] = Field(
        None, description="Maximum value (inclusive)"
    )

    @validator("max_value")
    def validate_range(cls, v, values):
        if v is not None and "min_value" in values and values["min_value"] is not None:
            if v < values["min_value"]:
                raise ValueError("Maximum value must be greater than minimum value")
        return v


class TextSearchFilter(BaseModel):
    """Text search filter parameters."""

    query: Optional[str] = Field(None, description="Search query text")
    case_sensitive: bool = Field(False, description="Whether search is case sensitive")
    exact_match: bool = Field(False, description="Whether to match exact text")

    @validator("query")
    def validate_query(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError("Search query must be at least 2 characters long")
        return v
