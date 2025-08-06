from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.common_deps import CurrentUserDep, InventoryServiceDep, StaffUserDep
from app.schemas.inventory import (
    InventoryItem,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemWithType,
)
from app.schemas.responses import MessageResponse

router = APIRouter()


@router.post("/", response_model=InventoryItem)
async def create_inventory_item(
    inventory_item_data: InventoryItemCreate,
    service: InventoryServiceDep,
    current_user: StaffUserDep,
):
    """Create a new inventory item"""
    return await service.create_inventory_item(inventory_item_data)


@router.get("/", response_model=List[InventoryItemWithType])
async def get_inventory_items(
    service: InventoryServiceDep,
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    type_id: Optional[int] = Query(None, description="Filter by inventory type ID"),
    available_only: bool = Query(False, description="Filter available items only"),
):
    """Get list of inventory items"""
    items = await service.get_inventory_items(skip, limit, type_id, available_only)

    return items


@router.get("/{inventory_item_id}", response_model=InventoryItemWithType)
async def get_inventory_item(
    inventory_item_id: int,
    service: InventoryServiceDep,
    current_user: CurrentUserDep,
):
    """Get inventory item by ID"""
    item = await service.get_inventory_item(inventory_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    return item


@router.put("/{inventory_item_id}", response_model=InventoryItem)
async def update_inventory_item(
    inventory_item_id: int,
    inventory_item_data: InventoryItemUpdate,
    service: InventoryServiceDep,
    current_user: StaffUserDep,
):
    """Update inventory item"""
    return await service.update_inventory_item(inventory_item_id, inventory_item_data)


@router.delete("/{inventory_item_id}", response_model=MessageResponse)
async def delete_inventory_item(
    inventory_item_id: int,
    service: InventoryServiceDep,
    current_user: StaffUserDep,
):
    """Delete inventory item"""
    await service.delete_inventory_item(inventory_item_id)
    return MessageResponse(message="Inventory item deleted successfully")


@router.get("/by-type/{type_id}/available", response_model=List[InventoryItemWithType])
async def get_available_items_by_type(
    type_id: int,
    service: InventoryServiceDep,
    current_user: CurrentUserDep,
):
    """Get available inventory items of a specific type"""
    items = await service.get_available_items_by_type(type_id)

    return items
