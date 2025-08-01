from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_active_user
from app.models.user import User, UserRole
from app.schemas.custom_item import (
    CustomItem,
    CustomItemCreate,
    CustomItemUpdate,
)
from app.schemas.responses import MessageResponse
from app.services.custom_item_service import CustomItemService

router = APIRouter()


async def require_staff_role(current_user: User = Depends(get_active_user)):
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff role required")
    return current_user


@router.post("/", response_model=CustomItem)
async def create_custom_item(
    custom_item_data: CustomItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create a new custom item/service"""
    service = CustomItemService(db)
    return await service.create_custom_item(custom_item_data)


@router.get("/", response_model=List[CustomItem])
async def get_custom_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True, description="Filter active items only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get list of custom items/services"""
    service = CustomItemService(db)
    return await service.get_custom_items(skip, limit, active_only)


@router.get("/{custom_item_id}", response_model=CustomItem)
async def get_custom_item(
    custom_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get custom item by ID"""
    service = CustomItemService(db)
    custom_item = await service.get_custom_item(custom_item_id)
    if not custom_item:
        raise HTTPException(status_code=404, detail="Custom item not found")
    return custom_item


@router.put("/{custom_item_id}", response_model=CustomItem)
async def update_custom_item(
    custom_item_id: int,
    custom_item_data: CustomItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Update custom item"""
    service = CustomItemService(db)
    return await service.update_custom_item(custom_item_id, custom_item_data)


@router.delete("/{custom_item_id}", response_model=MessageResponse)
async def delete_custom_item(
    custom_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Delete custom item"""
    service = CustomItemService(db)
    await service.delete_custom_item(custom_item_id)
    return MessageResponse(message="Custom item deleted successfully")
