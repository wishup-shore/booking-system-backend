"""
Centralized authentication dependencies.

This module provides centralized authentication and authorization dependencies,
eliminating the duplication of require_staff_role functions across endpoint files.
"""

from typing import Annotated
from fastapi import Depends

from app.core.security import get_active_user
from app.core.service_utils import (
    ensure_staff_access,
    ensure_user_or_staff_access,
    ensure_active_user,
)
from app.models.user import User


def require_staff_role() -> User:
    """
    Dependency that requires staff role access.

    Returns:
        User with staff role

    Raises:
        AccessDeniedError: If user doesn't have staff role
        InactiveUserError: If user is inactive
    """

    def dependency(current_user: User = Depends(get_active_user)) -> User:
        return ensure_staff_access(current_user)

    return dependency


def require_user_or_staff_role() -> User:
    """
    Dependency that requires user or staff role access.

    Returns:
        User with user or staff role

    Raises:
        AccessDeniedError: If user doesn't have sufficient role
        InactiveUserError: If user is inactive
    """

    def dependency(current_user: User = Depends(get_active_user)) -> User:
        return ensure_user_or_staff_access(current_user)

    return dependency


def require_active_user() -> User:
    """
    Dependency that requires an active user (any role).

    Returns:
        Active user

    Raises:
        InactiveUserError: If user is inactive
    """

    def dependency(current_user: User = Depends(get_active_user)) -> User:
        return ensure_active_user(current_user)

    return dependency


# Pre-configured dependency instances for common use
RequireStaffRole = Annotated[User, Depends(require_staff_role())]
RequireUserOrStaffRole = Annotated[User, Depends(require_user_or_staff_role())]
RequireActiveUser = Annotated[User, Depends(require_active_user())]

# Legacy compatibility - single instances for backward compatibility
require_staff = require_staff_role()
require_user_or_staff = require_user_or_staff_role()
require_active = require_active_user()
