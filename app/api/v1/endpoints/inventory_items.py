from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_active_user
from app.models.user import User, UserRole
from app.schemas.inventory import (
    InventoryItem,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemWithType,
)
from app.schemas.responses import MessageResponse
from app.services.inventory_service import InventoryService

router = APIRouter()


async def require_staff_role(current_user: User = Depends(get_active_user)):
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff role required")
    return current_user


@router.post("/", response_model=InventoryItem)
async def create_inventory_item(
    inventory_item_data: InventoryItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create a new inventory item"""
    service = InventoryService(db)
    return await service.create_inventory_item(inventory_item_data)


@router.get("/", response_model=List[InventoryItemWithType])
async def get_inventory_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    type_id: Optional[int] = Query(None, description="Filter by inventory type ID"),
    available_only: bool = Query(False, description="Filter available items only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get list of inventory items"""
    service = InventoryService(db)
    items = await service.get_inventory_items(skip, limit, type_id, available_only)

    return items


@router.get("/{inventory_item_id}", response_model=InventoryItemWithType)
async def get_inventory_item(
    inventory_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get inventory item by ID"""
    service = InventoryService(db)
    item = await service.get_inventory_item(inventory_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    return item


@router.put("/{inventory_item_id}", response_model=InventoryItem)
async def update_inventory_item(
    inventory_item_id: int,
    inventory_item_data: InventoryItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Update inventory item"""
    service = InventoryService(db)
    return await service.update_inventory_item(inventory_item_id, inventory_item_data)


@router.delete("/{inventory_item_id}", response_model=MessageResponse)
async def delete_inventory_item(
    inventory_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Delete inventory item"""
    service = InventoryService(db)
    await service.delete_inventory_item(inventory_item_id)
    return MessageResponse(message="Inventory item deleted successfully")


@router.get("/by-type/{type_id}/available", response_model=List[InventoryItemWithType])
async def get_available_items_by_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get available inventory items of a specific type"""
    service = InventoryService(db)
    items = await service.get_available_items_by_type(type_id)

    return items
