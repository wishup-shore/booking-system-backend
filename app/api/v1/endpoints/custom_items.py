from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.core.common_deps import CurrentUserDep, CustomItemServiceDep, StaffUserDep
from app.schemas.custom_item import (
    CustomItem,
    CustomItemCreate,
    CustomItemUpdate,
)
from app.schemas.responses import MessageResponse

router = APIRouter()


@router.post("/", response_model=CustomItem)
async def create_custom_item(
    custom_item_data: CustomItemCreate,
    service: CustomItemServiceDep,
    current_user: StaffUserDep,
):
    """Create a new custom item/service"""
    return await service.create_custom_item(custom_item_data)


@router.get("/", response_model=List[CustomItem])
async def get_custom_items(
    service: CustomItemServiceDep,
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True, description="Filter active items only"),
):
    """Get list of custom items/services"""
    return await service.get_custom_items(skip, limit, active_only)


@router.get("/{custom_item_id}", response_model=CustomItem)
async def get_custom_item(
    custom_item_id: int,
    service: CustomItemServiceDep,
    current_user: CurrentUserDep,
):
    """Get custom item by ID"""
    custom_item = await service.get_custom_item(custom_item_id)
    if not custom_item:
        raise HTTPException(status_code=404, detail="Custom item not found")
    return custom_item


@router.put("/{custom_item_id}", response_model=CustomItem)
async def update_custom_item(
    custom_item_id: int,
    custom_item_data: CustomItemUpdate,
    service: CustomItemServiceDep,
    current_user: StaffUserDep,
):
    """Update custom item"""
    return await service.update_custom_item(custom_item_id, custom_item_data)


@router.delete("/{custom_item_id}", response_model=MessageResponse)
async def delete_custom_item(
    custom_item_id: int,
    service: CustomItemServiceDep,
    current_user: StaffUserDep,
):
    """Delete custom item"""
    await service.delete_custom_item(custom_item_id)
    return MessageResponse(message="Custom item deleted successfully")
