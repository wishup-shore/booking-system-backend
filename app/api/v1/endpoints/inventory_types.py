from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.core.common_deps import CurrentUserDep, InventoryServiceDep, StaffUserDep
from app.schemas.inventory import (
    InventoryType,
    InventoryTypeCreate,
    InventoryTypeUpdate,
)
from app.schemas.responses import MessageResponse

router = APIRouter()


@router.post("/", response_model=InventoryType)
async def create_inventory_type(
    inventory_type_data: InventoryTypeCreate,
    service: InventoryServiceDep,
    current_user: StaffUserDep,
):
    """Create a new inventory type"""
    return await service.create_inventory_type(inventory_type_data)


@router.get("/", response_model=List[InventoryType])
async def get_inventory_types(
    service: InventoryServiceDep,
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True, description="Filter active types only"),
):
    """Get list of inventory types"""
    return await service.get_inventory_types(skip, limit, active_only)


@router.get("/{inventory_type_id}", response_model=InventoryType)
async def get_inventory_type(
    inventory_type_id: int,
    service: InventoryServiceDep,
    current_user: CurrentUserDep,
):
    """Get inventory type by ID"""
    inventory_type = await service.get_inventory_type(inventory_type_id)
    if not inventory_type:
        raise HTTPException(status_code=404, detail="Inventory type not found")
    return inventory_type


@router.put("/{inventory_type_id}", response_model=InventoryType)
async def update_inventory_type(
    inventory_type_id: int,
    inventory_type_data: InventoryTypeUpdate,
    service: InventoryServiceDep,
    current_user: StaffUserDep,
):
    """Update inventory type"""
    return await service.update_inventory_type(inventory_type_id, inventory_type_data)


@router.delete("/{inventory_type_id}", response_model=MessageResponse)
async def delete_inventory_type(
    inventory_type_id: int,
    service: InventoryServiceDep,
    current_user: StaffUserDep,
):
    """Delete inventory type"""
    await service.delete_inventory_type(inventory_type_id)
    return MessageResponse(message="Inventory type deleted successfully")
