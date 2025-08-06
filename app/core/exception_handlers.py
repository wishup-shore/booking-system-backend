"""
Exception handlers for converting domain exceptions to HTTP responses.

This module provides centralized exception handling that converts domain-level exceptions
into appropriate HTTP responses with consistent formatting and status codes.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    AccessDeniedError,
    BusinessRuleViolationError,
    ConflictError,
    DomainException,
    EntityNotFoundError,
    InactiveUserError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    error_type: Optional[str] = None,
) -> JSONResponse:
    """Create a standardized error response."""
    content = {
        "detail": message,
    }

    if error_type:
        content["error_type"] = error_type

    if details:
        content["details"] = details

    return JSONResponse(status_code=status_code, content=content)


async def entity_not_found_handler(
    request: Request, exc: EntityNotFoundError
) -> JSONResponse:
    """Handle EntityNotFoundError exceptions."""
    logger.info(f"Entity not found: {exc.entity_name} (id: {exc.entity_id})")

    return create_error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message=exc.message,
        details=exc.details,
        error_type="entity_not_found",
    )


async def access_denied_handler(
    request: Request, exc: AccessDeniedError
) -> JSONResponse:
    """Handle AccessDeniedError exceptions."""
    logger.warning(f"Access denied: {exc.message} for {request.url}")

    return create_error_response(
        status_code=status.HTTP_403_FORBIDDEN,
        message=exc.message,
        details=exc.details,
        error_type="access_denied",
    )


async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle ValidationError exceptions."""
    logger.warning(f"Validation error: {exc.message}")

    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=exc.message,
        details=exc.details,
        error_type="validation_error",
    )


async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
    """Handle ConflictError exceptions."""
    logger.warning(f"Conflict error: {exc.message}")

    return create_error_response(
        status_code=status.HTTP_409_CONFLICT,
        message=exc.message,
        details=exc.details,
        error_type="conflict_error",
    )


async def business_rule_violation_handler(
    request: Request, exc: BusinessRuleViolationError
) -> JSONResponse:
    """Handle BusinessRuleViolationError exceptions."""
    logger.warning(f"Business rule violation: {exc.rule_name} - {exc.message}")

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message=exc.message,
        details=exc.details,
        error_type="business_rule_violation",
    )


async def inactive_user_handler(
    request: Request, exc: InactiveUserError
) -> JSONResponse:
    """Handle InactiveUserError exceptions."""
    logger.warning(f"Inactive user attempted operation: {request.url}")

    return create_error_response(
        status_code=status.HTTP_403_FORBIDDEN,
        message=exc.message,
        error_type="inactive_user",
    )


async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    """Handle generic DomainException exceptions."""
    logger.error(f"Unhandled domain exception: {exc.message}")

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An internal error occurred",
        error_type="domain_error",
    )


async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    """Handle SQLAlchemy IntegrityError exceptions."""
    logger.error(f"Database integrity error: {str(exc)}")

    # Common integrity constraint violations
    error_message = "Database constraint violation"
    if "unique constraint" in str(exc).lower():
        error_message = "A record with this value already exists"
    elif "foreign key constraint" in str(exc).lower():
        error_message = "Referenced record does not exist"
    elif "not null constraint" in str(exc).lower():
        error_message = "Required field is missing"

    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=error_message,
        error_type="integrity_error",
    )


async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI request validation errors."""
    logger.warning(f"Request validation error: {exc.errors()}")

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Request validation failed",
        details={"validation_errors": exc.errors()},
        error_type="request_validation_error",
    )


# Exception handler mapping
EXCEPTION_HANDLERS = {
    EntityNotFoundError: entity_not_found_handler,
    AccessDeniedError: access_denied_handler,
    ValidationError: validation_error_handler,
    ConflictError: conflict_error_handler,
    BusinessRuleViolationError: business_rule_violation_handler,
    InactiveUserError: inactive_user_handler,
    DomainException: domain_exception_handler,
    IntegrityError: integrity_error_handler,
    RequestValidationError: request_validation_error_handler,
}
