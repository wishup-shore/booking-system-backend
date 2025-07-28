from fastapi import APIRouter

from app.api.v1.endpoints import accommodation_types, accommodations, auth

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(accommodation_types.router, prefix="/accommodation-types", tags=["accommodation-types"])
api_router.include_router(accommodations.router, prefix="/accommodations", tags=["accommodations"])