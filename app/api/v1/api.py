from fastapi import APIRouter

from app.api.v1.endpoints import (
    accommodation_types,
    accommodations,
    auth,
    batch,
    bookings,
    clients,
    custom_items,
    inventory_items,
    inventory_types,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(
    accommodation_types.router,
    prefix="/accommodation-types",
    tags=["accommodation-types"],
)
api_router.include_router(
    accommodations.router, prefix="/accommodations", tags=["accommodations"]
)
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(
    inventory_types.router, prefix="/inventory-types", tags=["inventory-types"]
)
api_router.include_router(
    inventory_items.router, prefix="/inventory-items", tags=["inventory-items"]
)
api_router.include_router(
    custom_items.router, prefix="/custom-items", tags=["custom-items"]
)
api_router.include_router(batch.router, prefix="/batch", tags=["batch-operations"])
