from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_active_user
from app.models.user import User, UserRole
from app.schemas.inventory import (
    InventoryType,
    InventoryTypeCreate,
    InventoryTypeUpdate,
)
from app.schemas.responses import MessageResponse
from app.services.inventory_service import InventoryService

router = APIRouter()


async def require_staff_role(current_user: User = Depends(get_active_user)):
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff role required")
    return current_user


@router.post("/", response_model=InventoryType)
async def create_inventory_type(
    inventory_type_data: InventoryTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create a new inventory type"""
    service = InventoryService(db)
    return await service.create_inventory_type(inventory_type_data)


@router.get("/", response_model=List[InventoryType])
async def get_inventory_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True, description="Filter active types only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get list of inventory types"""
    service = InventoryService(db)
    return await service.get_inventory_types(skip, limit, active_only)


@router.get("/{inventory_type_id}", response_model=InventoryType)
async def get_inventory_type(
    inventory_type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    """Get inventory type by ID"""
    service = InventoryService(db)
    inventory_type = await service.get_inventory_type(inventory_type_id)
    if not inventory_type:
        raise HTTPException(status_code=404, detail="Inventory type not found")
    return inventory_type


@router.put("/{inventory_type_id}", response_model=InventoryType)
async def update_inventory_type(
    inventory_type_id: int,
    inventory_type_data: InventoryTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Update inventory type"""
    service = InventoryService(db)
    return await service.update_inventory_type(inventory_type_id, inventory_type_data)


@router.delete("/{inventory_type_id}", response_model=MessageResponse)
async def delete_inventory_type(
    inventory_type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Delete inventory type"""
    service = InventoryService(db)
    await service.delete_inventory_type(inventory_type_id)
    return MessageResponse(message="Inventory type deleted successfully")
