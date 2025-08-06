"""
Common dependencies for the booking system.

This module provides convenient access to commonly used dependencies,
reducing boilerplate code in endpoint functions.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import (
    RequireActiveUser,
    RequireStaffRole,
    RequireUserOrStaffRole,
)
from app.core.database import get_db
from app.core.security import get_active_user
from app.core.service_deps import (
    GetAccommodationService,
    GetAccommodationTypeService,
    GetAuthService,
    GetBatchOperationService,
    GetBookingService,
    GetCalendarService,
    GetClientGroupService,
    GetClientService,
    GetCustomItemService,
    GetInventoryService,
)
from app.models.user import User

# Database dependencies
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]

# User dependencies
CurrentUserDep = Annotated[User, Depends(get_active_user)]

# Commonly used type aliases for endpoint signatures
StaffUserDep = RequireStaffRole
UserOrStaffDep = RequireUserOrStaffRole
ActiveUserDep = RequireActiveUser

# Service type aliases for cleaner endpoint signatures
AccommodationServiceDep = GetAccommodationService
AccommodationTypeServiceDep = GetAccommodationTypeService
BookingServiceDep = GetBookingService
ClientServiceDep = GetClientService
ClientGroupServiceDep = GetClientGroupService
AuthServiceDep = GetAuthService
CalendarServiceDep = GetCalendarService
InventoryServiceDep = GetInventoryService
CustomItemServiceDep = GetCustomItemService
BatchOperationServiceDep = GetBatchOperationService
