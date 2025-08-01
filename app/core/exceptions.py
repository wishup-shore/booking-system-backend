"""
Domain exceptions for the booking system.

These exceptions represent business domain errors and are converted to HTTP responses
by the exception handler middleware. This separates business logic concerns from HTTP concerns.
"""

from typing import Optional


class DomainException(Exception):
    """Base exception for all domain-level errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class EntityNotFoundError(DomainException):
    """Raised when a requested entity is not found in the database."""

    def __init__(
        self,
        entity_name: str,
        entity_id: Optional[int] = None,
        field_name: Optional[str] = None,
    ):
        self.entity_name = entity_name
        self.entity_id = entity_id
        self.field_name = field_name

        if entity_id:
            message = f"{entity_name} with id {entity_id} not found"
        elif field_name:
            message = f"{entity_name} not found"
        else:
            message = f"{entity_name} not found"

        super().__init__(message, {"entity_name": entity_name, "entity_id": entity_id})


class AccessDeniedError(DomainException):
    """Raised when user lacks required permissions for an operation."""

    def __init__(self, required_role: str, current_role: Optional[str] = None):
        self.required_role = required_role
        self.current_role = current_role

        message = f"{required_role} role required"
        if current_role:
            message += f", but current role is {current_role}"

        super().__init__(
            message, {"required_role": required_role, "current_role": current_role}
        )


class ValidationError(DomainException):
    """Raised when business rule validation fails."""

    def __init__(
        self, message: str, field: Optional[str] = None, value: Optional[str] = None
    ):
        self.field = field
        self.value = value
        super().__init__(message, {"field": field, "value": value})


class ConflictError(DomainException):
    """Raised when an operation conflicts with existing data or business rules."""

    def __init__(self, message: str, conflicting_entity: Optional[str] = None):
        self.conflicting_entity = conflicting_entity
        super().__init__(message, {"conflicting_entity": conflicting_entity})


class BusinessRuleViolationError(DomainException):
    """Raised when a business rule is violated."""

    def __init__(self, rule_name: str, message: str, context: Optional[dict] = None):
        self.rule_name = rule_name
        super().__init__(message, {"rule_name": rule_name, **(context or {})})


class InactiveUserError(DomainException):
    """Raised when an inactive user attempts to perform operations."""

    def __init__(self):
        super().__init__("User account is inactive")
