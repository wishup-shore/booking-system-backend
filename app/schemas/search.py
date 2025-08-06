from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.pagination import (
    DateRangeFilter,
    FilterParams,
    NumericRangeFilter,
    PaginationParams,
    SortParams,
    TextSearchFilter,
)
from app.models.accommodation import AccommodationCondition, AccommodationStatus
from app.models.booking import BookingStatus, PaymentStatus


class SearchEntityType(str, Enum):
    """Types of entities that can be searched."""

    BOOKINGS = "bookings"
    CLIENTS = "clients"
    ACCOMMODATIONS = "accommodations"
    INVENTORY = "inventory"
    ALL = "all"


class BookingSearchFilters(FilterParams):
    """Advanced search filters for bookings."""

    # Status filters
    statuses: Optional[List[BookingStatus]] = Field(
        None, description="Filter by booking statuses"
    )
    payment_statuses: Optional[List[PaymentStatus]] = Field(
        None, description="Filter by payment statuses"
    )

    # Date filters
    check_in_date_range: Optional[DateRangeFilter] = Field(
        None, description="Check-in date range"
    )
    check_out_date_range: Optional[DateRangeFilter] = Field(
        None, description="Check-out date range"
    )
    created_date_range: Optional[DateRangeFilter] = Field(
        None, description="Booking creation date range"
    )

    # Client filters
    client_name: Optional[str] = Field(None, description="Search by client name")
    client_phone: Optional[str] = Field(None, description="Search by client phone")
    client_email: Optional[str] = Field(None, description="Search by client email")
    client_ids: Optional[List[int]] = Field(
        None, description="Filter by specific client IDs"
    )
    client_group_ids: Optional[List[int]] = Field(
        None, description="Filter by client group IDs"
    )

    # Accommodation filters
    accommodation_ids: Optional[List[int]] = Field(
        None, description="Filter by specific accommodation IDs"
    )
    accommodation_type_ids: Optional[List[int]] = Field(
        None, description="Filter by accommodation type IDs"
    )
    accommodation_numbers: Optional[List[str]] = Field(
        None, description="Filter by accommodation numbers"
    )

    # Numeric filters
    guest_count_range: Optional[NumericRangeFilter] = Field(
        None, description="Guest count range"
    )
    total_amount_range: Optional[NumericRangeFilter] = Field(
        None, description="Total amount range"
    )
    paid_amount_range: Optional[NumericRangeFilter] = Field(
        None, description="Paid amount range"
    )

    # Special filters
    is_open_dates: Optional[bool] = Field(
        None, description="Filter open dates bookings"
    )
    has_inventory_items: Optional[bool] = Field(
        None, description="Filter bookings with inventory items"
    )
    has_custom_items: Optional[bool] = Field(
        None, description="Filter bookings with custom items"
    )

    # Text search
    text_search: Optional[TextSearchFilter] = Field(
        None, description="General text search across relevant fields"
    )
    comments_search: Optional[str] = Field(
        None, description="Search in booking comments"
    )


class ClientSearchFilters(FilterParams):
    """Advanced search filters for clients."""

    # Text search
    text_search: Optional[TextSearchFilter] = Field(
        None, description="Search by name, phone, email"
    )
    first_name: Optional[str] = Field(None, description="Search by first name")
    last_name: Optional[str] = Field(None, description="Search by last name")
    phone: Optional[str] = Field(None, description="Search by phone number")
    email: Optional[str] = Field(None, description="Search by email")

    # Group filters
    group_ids: Optional[List[int]] = Field(
        None, description="Filter by client group IDs"
    )
    has_group: Optional[bool] = Field(
        None, description="Filter clients with/without groups"
    )

    # Rating filter
    rating_range: Optional[NumericRangeFilter] = Field(
        None, description="Client rating range"
    )

    # Date filters
    created_date_range: Optional[DateRangeFilter] = Field(
        None, description="Client creation date range"
    )

    # Booking-related filters
    has_bookings: Optional[bool] = Field(
        None, description="Filter clients with/without bookings"
    )
    booking_status_filter: Optional[List[BookingStatus]] = Field(
        None, description="Filter clients by their booking statuses"
    )
    last_booking_date_range: Optional[DateRangeFilter] = Field(
        None, description="Filter by last booking date range"
    )
    total_bookings_range: Optional[NumericRangeFilter] = Field(
        None, description="Filter by total number of bookings"
    )

    # Special filters
    car_numbers: Optional[List[str]] = Field(None, description="Filter by car numbers")
    has_photo: Optional[bool] = Field(
        None, description="Filter clients with/without photos"
    )
    comments_search: Optional[str] = Field(
        None, description="Search in client comments"
    )


class AccommodationSearchFilters(FilterParams):
    """Advanced search filters for accommodations."""

    # Basic filters
    accommodation_type_ids: Optional[List[int]] = Field(
        None, description="Filter by accommodation type IDs"
    )
    statuses: Optional[List[AccommodationStatus]] = Field(
        None, description="Filter by accommodation statuses"
    )
    conditions: Optional[List[AccommodationCondition]] = Field(
        None, description="Filter by accommodation conditions"
    )

    # Numeric filters
    capacity_range: Optional[NumericRangeFilter] = Field(
        None, description="Capacity range"
    )
    price_range: Optional[NumericRangeFilter] = Field(
        None, description="Price per night range"
    )

    # Text search
    text_search: Optional[TextSearchFilter] = Field(
        None, description="Search by number, type name"
    )
    number: Optional[str] = Field(None, description="Search by accommodation number")
    comments_search: Optional[str] = Field(
        None, description="Search in accommodation comments"
    )

    # Availability filters
    available_for_dates: Optional[DateRangeFilter] = Field(
        None, description="Filter accommodations available for date range"
    )

    # Usage statistics filters
    occupancy_rate_range: Optional[NumericRangeFilter] = Field(
        None, description="Filter by occupancy rate percentage"
    )


class GlobalSearchRequest(BaseModel):
    """Global search across multiple entity types."""

    query: str = Field(..., min_length=2, description="Search query text")
    entities: List[SearchEntityType] = Field(
        default=[SearchEntityType.ALL], description="Entity types to search in"
    )
    pagination: PaginationParams = Field(default_factory=PaginationParams)
    sort: SortParams = Field(default_factory=SortParams)

    # Entity-specific filters (applied only when searching specific entities)
    booking_filters: Optional[BookingSearchFilters] = None
    client_filters: Optional[ClientSearchFilters] = None
    accommodation_filters: Optional[AccommodationSearchFilters] = None


class BookingSearchRequest(BaseModel):
    """Booking-specific search request."""

    filters: BookingSearchFilters = Field(default_factory=BookingSearchFilters)
    pagination: PaginationParams = Field(default_factory=PaginationParams)
    sort: SortParams = Field(
        default_factory=lambda: SortParams(sort_by="created_at", sort_direction="desc")
    )

    include_details: bool = Field(
        default=True, description="Include client and accommodation details in response"
    )
    include_items: bool = Field(
        default=False, description="Include inventory and custom items in response"
    )


class ClientSearchRequest(BaseModel):
    """Client-specific search request."""

    filters: ClientSearchFilters = Field(default_factory=ClientSearchFilters)
    pagination: PaginationParams = Field(default_factory=PaginationParams)
    sort: SortParams = Field(
        default_factory=lambda: SortParams(sort_by="created_at", sort_direction="desc")
    )

    include_stats: bool = Field(
        default=False, description="Include client statistics in response"
    )
    include_booking_summary: bool = Field(
        default=False, description="Include booking summary in response"
    )


class AccommodationSearchRequest(BaseModel):
    """Accommodation-specific search request."""

    filters: AccommodationSearchFilters = Field(
        default_factory=AccommodationSearchFilters
    )
    pagination: PaginationParams = Field(default_factory=PaginationParams)
    sort: SortParams = Field(
        default_factory=lambda: SortParams(sort_by="number", sort_direction="asc")
    )

    include_current_booking: bool = Field(
        default=False, description="Include current booking information if occupied"
    )
    include_availability_calendar: bool = Field(
        default=False, description="Include next 30 days availability calendar"
    )


class SearchResultItem(BaseModel):
    """Individual search result item with metadata."""

    entity_type: SearchEntityType
    entity_id: int
    title: str = Field(description="Display title for the result")
    subtitle: Optional[str] = Field(None, description="Additional information")
    relevance_score: float = Field(description="Relevance score for ranking")
    highlight: Optional[Dict[str, List[str]]] = Field(
        None, description="Highlighted text matches"
    )
    data: Dict[str, Any] = Field(description="Entity data")


class GlobalSearchResponse(BaseModel):
    """Global search response with results from multiple entity types."""

    query: str
    total_results: int
    results_by_entity: Dict[SearchEntityType, List[SearchResultItem]]
    pagination: Dict[str, Any]
    search_metadata: Dict[str, Any]


class SearchAggregation(BaseModel):
    """Search result aggregations for faceted search."""

    field: str
    values: Dict[str, int]  # value -> count


class SearchFacets(BaseModel):
    """Search facets for filtering results."""

    status_counts: Optional[Dict[str, int]] = None
    payment_status_counts: Optional[Dict[str, int]] = None
    accommodation_type_counts: Optional[Dict[str, int]] = None
    date_range_counts: Optional[Dict[str, int]] = None


class AdvancedSearchResponse(BaseModel):
    """Advanced search response with facets and aggregations."""

    items: List[Any]
    pagination: Dict[str, Any]
    facets: Optional[SearchFacets] = None
    aggregations: Optional[List[SearchAggregation]] = None
    search_metadata: Dict[str, Any]


class SearchSuggestion(BaseModel):
    """Search suggestion for autocomplete."""

    text: str
    type: SearchEntityType
    count: int = Field(description="Number of matching results")


class SearchSuggestionsRequest(BaseModel):
    """Request for search suggestions."""

    query: str = Field(..., min_length=1, max_length=100)
    entity_types: List[SearchEntityType] = Field(default=[SearchEntityType.ALL])
    limit: int = Field(default=10, ge=1, le=50)


class SearchSuggestionsResponse(BaseModel):
    """Response with search suggestions."""

    suggestions: List[SearchSuggestion]
    query: str


class SearchHistoryItem(BaseModel):
    """Search history item for user search tracking."""

    query: str
    entity_type: SearchEntityType
    filters_used: Dict[str, Any]
    results_count: int
    search_time: datetime
    user_id: Optional[int] = None


class PopularSearchesResponse(BaseModel):
    """Response with popular search queries."""

    searches: List[Dict[str, Any]]
    period: str = Field(description="Time period for popular searches")


# Validation functions for search requests
def validate_booking_search_request(
    request: BookingSearchRequest,
) -> BookingSearchRequest:
    """Validate and normalize booking search request."""
    # Add business logic validation here
    return request


def validate_client_search_request(request: ClientSearchRequest) -> ClientSearchRequest:
    """Validate and normalize client search request."""
    # Add business logic validation here
    return request


def validate_accommodation_search_request(
    request: AccommodationSearchRequest,
) -> AccommodationSearchRequest:
    """Validate and normalize accommodation search request."""
    # Add business logic validation here
    return request
