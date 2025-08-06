"""
Service layer utility functions.

This module provides centralized utilities for common service layer patterns,
eliminating code duplication and ensuring consistent behavior across services.
"""

from typing import Any, Optional, TypeVar

from app.core.exceptions import (
    AccessDeniedError,
    ConflictError,
    EntityNotFoundError,
    InactiveUserError,
    ValidationError,
)
from app.models.user import User, UserRole

T = TypeVar("T")


def ensure_exists(
    entity: Optional[T],
    entity_name: str,
    entity_id: Optional[int] = None,
    field_name: Optional[str] = None,
) -> T:
    """
    Ensure an entity exists, raising EntityNotFoundError if it doesn't.

    This centralizes the common pattern of checking if an entity exists
    and raising an appropriate exception if it doesn't.

    Args:
        entity: The entity to check (can be None)
        entity_name: Human-readable name of the entity type (e.g., "Booking", "Client")
        entity_id: Optional ID of the entity for more specific error messages
        field_name: Optional field name for more specific error messages

    Returns:
        The entity if it exists

    Raises:
        EntityNotFoundError: If the entity is None
    """
    if entity is None:
        raise EntityNotFoundError(entity_name, entity_id, field_name)
    return entity


def ensure_staff_access(user: User) -> User:
    """
    Ensure user has staff role access.

    Args:
        user: User to check

    Returns:
        The user if they have staff access

    Raises:
        AccessDeniedError: If user doesn't have staff role
        InactiveUserError: If user is inactive
    """
    if not user.is_active:
        raise InactiveUserError()

    if user.role != UserRole.STAFF:
        raise AccessDeniedError("Staff", user.role.value)

    return user


def ensure_user_or_staff_access(user: User) -> User:
    """
    Ensure user has at least user-level access (USER or STAFF role).

    Args:
        user: User to check

    Returns:
        The user if they have appropriate access

    Raises:
        AccessDeniedError: If user doesn't have sufficient role
        InactiveUserError: If user is inactive
    """
    if not user.is_active:
        raise InactiveUserError()

    if user.role not in [UserRole.VIEWER, UserRole.STAFF]:
        raise AccessDeniedError("User or Staff", user.role.value)

    return user


def ensure_active_user(user: User) -> User:
    """
    Ensure user is active.

    Args:
        user: User to check

    Returns:
        The user if they are active

    Raises:
        InactiveUserError: If user is inactive
    """
    if not user.is_active:
        raise InactiveUserError()
    return user


def validate_positive_integer(value: int, field_name: str) -> int:
    """
    Validate that a value is a positive integer.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages

    Returns:
        The value if valid

    Raises:
        ValidationError: If value is not positive
    """
    if value <= 0:
        raise ValidationError(
            f"{field_name} must be greater than 0", field_name, str(value)
        )
    return value


def validate_non_empty_string(value: Optional[str], field_name: str) -> str:
    """
    Validate that a string value is not None or empty.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages

    Returns:
        The value if valid

    Raises:
        ValidationError: If value is None or empty
    """
    if not value or not value.strip():
        raise ValidationError(f"{field_name} cannot be empty", field_name, value)
    return value.strip()


def validate_date_range(
    start_date: Any,
    end_date: Any,
    start_field: str = "start_date",
    end_field: str = "end_date",
) -> None:
    """
    Validate that end date is after start date.

    Args:
        start_date: Start date
        end_date: End date
        start_field: Name of start date field for error messages
        end_field: Name of end date field for error messages

    Raises:
        ValidationError: If end date is not after start date
    """
    if end_date <= start_date:
        raise ValidationError(
            f"{end_field} must be after {start_field}",
            end_field,
            f"{end_date} (start: {start_date})",
        )


def ensure_no_related_records(
    count: int, entity_name: str, related_entity: str
) -> None:
    """
    Ensure no related records exist before deletion.

    Args:
        count: Number of related records
        entity_name: Name of the entity being deleted
        related_entity: Name of the related entity type

    Raises:
        ConflictError: If related records exist
    """
    if count > 0:
        raise ConflictError(
            f"Cannot delete {entity_name} with existing {related_entity}",
            related_entity,
        )


def validate_unique_field(
    existing_entity: Optional[Any], field_name: str, field_value: str, entity_name: str
) -> None:
    """
    Validate that a field value is unique.

    Args:
        existing_entity: Existing entity with the same field value (if any)
        field_name: Name of the field
        field_value: Value of the field
        entity_name: Name of the entity type

    Raises:
        ConflictError: If field value is not unique
    """
    if existing_entity:
        raise ConflictError(
            f"{entity_name} with this {field_name} already exists", entity_name
        )
