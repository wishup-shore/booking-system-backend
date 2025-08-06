"""
Service dependency injection utilities.

This module provides centralized service instantiation through dependency injection,
eliminating the repeated pattern of manually creating service instances in endpoints.
"""

from typing import Annotated, Callable, Type, TypeVar

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.accommodation_service import (
    AccommodationService,
    AccommodationTypeService,
)
from app.services.auth_service import AuthService
from app.services.batch_service import BatchOperationService
from app.services.booking_service import BookingService
from app.services.calendar_service import CalendarService
from app.services.client_service import ClientGroupService, ClientService
from app.services.custom_item_service import CustomItemService
from app.services.inventory_service import InventoryService

T = TypeVar("T")


def get_service(service_class: Type[T]) -> Callable[[AsyncSession], T]:
    """
    Generic service dependency factory.

    Creates a dependency function that instantiates a service with a database session.

    Args:
        service_class: The service class to instantiate

    Returns:
        A dependency function that creates service instances
    """

    def dependency(db: AsyncSession = Depends(get_db)) -> T:
        return service_class(db)

    return dependency


# Pre-configured service dependencies
GetAccommodationService = Annotated[
    AccommodationService, Depends(get_service(AccommodationService))
]
GetAccommodationTypeService = Annotated[
    AccommodationTypeService, Depends(get_service(AccommodationTypeService))
]
GetBookingService = Annotated[BookingService, Depends(get_service(BookingService))]
GetClientService = Annotated[ClientService, Depends(get_service(ClientService))]
GetClientGroupService = Annotated[
    ClientGroupService, Depends(get_service(ClientGroupService))
]
GetAuthService = Annotated[AuthService, Depends(get_service(AuthService))]
GetCalendarService = Annotated[CalendarService, Depends(get_service(CalendarService))]
GetInventoryService = Annotated[
    InventoryService, Depends(get_service(InventoryService))
]
GetCustomItemService = Annotated[
    CustomItemService, Depends(get_service(CustomItemService))
]
GetBatchOperationService = Annotated[
    BatchOperationService, Depends(get_service(BatchOperationService))
]

# Legacy compatibility - individual dependency functions
get_accommodation_service = get_service(AccommodationService)
get_accommodation_type_service = get_service(AccommodationTypeService)
get_booking_service = get_service(BookingService)
get_client_service = get_service(ClientService)
get_client_group_service = get_service(ClientGroupService)
get_auth_service = get_service(AuthService)
get_calendar_service = get_service(CalendarService)
get_inventory_service = get_service(InventoryService)
get_custom_item_service = get_service(CustomItemService)
get_batch_operation_service = get_service(BatchOperationService)
