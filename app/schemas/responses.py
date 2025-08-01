"""
Common response schemas for API endpoints.

This module defines proper Pydantic models for endpoints that previously
returned raw dictionaries, ensuring clear Swagger documentation for frontend developers.
"""

from datetime import datetime
from typing import Optional, Any, List
from decimal import Decimal
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Standard response for operations that return a success message."""

    message: str = Field(
        ...,
        description="Success message describing the completed operation",
        example="Resource deleted successfully",
    )


class UserRegistrationResponse(BaseModel):
    """Response schema for user registration endpoint."""

    message: str = Field(
        ...,
        description="Registration success message",
        example="User created successfully",
    )
    user_id: int = Field(..., description="ID of the newly created user", example=123)


class CurrentUserResponse(BaseModel):
    """Response schema for /auth/me endpoint."""

    id: int = Field(..., description="User ID", example=1)
    username: str = Field(..., description="Username", example="john_doe")
    email: str = Field(
        ..., description="User email address", example="john@example.com"
    )
    role: str = Field(
        ..., description="User role (guest, user, staff)", example="staff"
    )
    is_active: bool = Field(
        ..., description="Whether the user account is active", example=True
    )


class AccommodationAvailabilityResponse(BaseModel):
    """Response schema for accommodation availability check."""

    accommodation_id: int = Field(
        ..., description="ID of the accommodation being checked", example=5
    )
    start_date: str = Field(
        ...,
        description="Check-in date in ISO format (YYYY-MM-DD)",
        example="2025-12-15",
    )
    end_date: str = Field(
        ...,
        description="Check-out date in ISO format (YYYY-MM-DD)",
        example="2025-12-18",
    )
    is_available: bool = Field(
        ...,
        description="Whether the accommodation is available for the specified dates",
        example=True,
    )


class AvailableAccommodation(BaseModel):
    """Schema for available accommodation information."""

    id: int = Field(..., description="Accommodation ID", example=1)
    number: str = Field(..., description="Room/accommodation number", example="101")
    type_name: str = Field(
        ...,
        description="Type of accommodation (e.g., Standard Room, Suite)",
        example="Standard Room",
    )
    capacity: int = Field(..., description="Maximum number of guests", example=2)
    price_per_night: Decimal = Field(
        ..., description="Price per night in local currency", example=150.00
    )
    status: str = Field(
        ..., description="Current accommodation status", example="available"
    )


class CalendarStatistics(BaseModel):
    """Response schema for calendar occupancy statistics."""

    total_accommodations: int = Field(
        ..., description="Total number of accommodations", example=50
    )
    occupied_nights: int = Field(
        ...,
        description="Total number of occupied accommodation-nights in the period",
        example=320,
    )
    available_nights: int = Field(
        ...,
        description="Total number of available accommodation-nights in the period",
        example=180,
    )
    occupancy_rate: float = Field(
        ..., description="Occupancy rate as a percentage (0-100)", example=64.0
    )
    total_revenue: Decimal = Field(
        ..., description="Total revenue for the period", example=48000.00
    )
    average_daily_rate: Decimal = Field(
        ..., description="Average daily rate (ADR) for occupied nights", example=150.00
    )
    revenue_per_available_room: Decimal = Field(
        ..., description="RevPAR (Revenue per Available Room)", example=96.00
    )
    period_start: str = Field(
        ...,
        description="Start date of the statistics period (YYYY-MM-DD)",
        example="2025-01-01",
    )
    period_end: str = Field(
        ...,
        description="End date of the statistics period (YYYY-MM-DD)",
        example="2025-01-31",
    )


class BookingActionResponse(BaseModel):
    """Response schema for booking-related actions (add/remove items)."""

    message: str = Field(
        ...,
        description="Success message describing the action performed",
        examples=[
            "Inventory item added to booking successfully",
            "Custom item removed from booking successfully",
        ],
    )
    booking_id: Optional[int] = Field(
        None, description="ID of the affected booking", example=123
    )
    item_id: Optional[int] = Field(
        None, description="ID of the affected item", example=456
    )


class InventoryItemAvailability(BaseModel):
    """Schema for inventory item availability information."""

    id: int = Field(..., description="Inventory item ID", example=1)
    number: str = Field(..., description="Item number/identifier", example="BIKE-001")
    type_name: str = Field(
        ..., description="Type of inventory item", example="Mountain Bike"
    )
    condition: str = Field(
        ..., description="Current condition of the item", example="excellent"
    )
    is_available: bool = Field(
        ..., description="Whether the item is currently available", example=True
    )
    comments: Optional[str] = Field(
        None, description="Additional notes about the item", example="Recently serviced"
    )


class BookingInventoryStatusResponse(BaseModel):
    """Response schema for booking inventory status operations."""

    booking_id: int = Field(..., description="Booking ID", example=123)
    inventory_items: List[InventoryItemAvailability] = Field(
        ..., description="List of inventory items associated with the booking"
    )
    total_items: int = Field(
        ..., description="Total number of inventory items in the booking", example=3
    )


class ErrorDetail(BaseModel):
    """Detailed error information."""

    type: str = Field(
        ..., description="Error type identifier", example="validation_error"
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        example="The requested resource was not found",
    )
    field: Optional[str] = Field(
        None,
        description="Field name if this is a field-specific error",
        example="email",
    )
    code: Optional[str] = Field(
        None,
        description="Application-specific error code",
        example="RESOURCE_NOT_FOUND",
    )


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: str = Field(..., description="Error summary", example="Validation failed")
    detail: str = Field(
        ...,
        description="Detailed error description",
        example="The email field is required and must be a valid email address",
    )
    timestamp: datetime = Field(
        ..., description="When the error occurred", example="2025-08-01T10:30:00Z"
    )
    path: str = Field(
        ...,
        description="API endpoint where the error occurred",
        example="/api/v1/users",
    )


class ValidationErrorResponse(BaseModel):
    """Response schema for validation errors."""

    error: str = Field(..., description="Error type", example="Validation Error")
    details: List[ErrorDetail] = Field(
        ..., description="List of specific validation errors"
    )
    timestamp: datetime = Field(..., description="When the validation error occurred")
    path: str = Field(..., description="API endpoint where the validation failed")


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total: int = Field(..., description="Total number of items available", example=250)
    page: int = Field(..., description="Current page number (1-based)", example=1)
    per_page: int = Field(..., description="Number of items per page", example=100)
    pages: int = Field(..., description="Total number of pages", example=3)
    has_next: bool = Field(
        ..., description="Whether there are more pages available", example=True
    )
    has_prev: bool = Field(
        ..., description="Whether there are previous pages", example=False
    )


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    data: List[Any] = Field(..., description="List of items for the current page")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class HealthCheckResponse(BaseModel):
    """Response schema for health check endpoints."""

    status: str = Field(..., description="Service health status", example="healthy")
    timestamp: datetime = Field(
        ..., description="Health check timestamp", example="2025-08-01T10:30:00Z"
    )
    version: str = Field(..., description="API version", example="1.0.0")
    database: str = Field(
        ..., description="Database connection status", example="connected"
    )
    uptime: int = Field(..., description="Service uptime in seconds", example=86400)
