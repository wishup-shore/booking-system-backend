from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_active_user
from app.models.user import User, UserRole
from app.schemas.client import (
    Client,
    ClientCreate,
    ClientUpdate,
    ClientWithStats,
    ClientGroup,
    ClientGroupCreate,
    ClientGroupUpdate,
)
from app.schemas.responses import MessageResponse
from app.services.client_service import ClientService, ClientGroupService

router = APIRouter()


async def require_staff_role(current_user: User = Depends(get_active_user)):
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff role required")
    return current_user


# Client endpoints
@router.get("/", response_model=List[Client])
async def get_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Search by name, phone, or email"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    service = ClientService(db)
    if search:
        return await service.search_clients(search, skip, limit)
    return await service.get_all(skip, limit)


@router.post("/", response_model=Client)
async def create_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientService(db)
    return await service.create(client_data)


@router.get("/{client_id}", response_model=Client)
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    service = ClientService(db)
    client = await service.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=Client)
async def update_client(
    client_id: int,
    client_data: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientService(db)
    return await service.update(client_id, client_data)


@router.delete("/{client_id}", response_model=MessageResponse)
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientService(db)
    await service.delete(client_id)
    return MessageResponse(message="Client deleted successfully")


@router.get("/{client_id}/stats", response_model=ClientWithStats)
async def get_client_stats(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    service = ClientService(db)
    return await service.get_client_stats(client_id)


# Client Group endpoints
@router.get("/groups/", response_model=List[ClientGroup])
async def get_client_groups(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_active_user)
):
    service = ClientGroupService(db)
    return await service.get_all()


@router.post("/groups/", response_model=ClientGroup)
async def create_client_group(
    group_data: ClientGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientGroupService(db)
    return await service.create(group_data)


@router.get("/groups/{group_id}", response_model=ClientGroup)
async def get_client_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    service = ClientGroupService(db)
    group = await service.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Client group not found")
    return group


@router.put("/groups/{group_id}", response_model=ClientGroup)
async def update_client_group(
    group_id: int,
    group_data: ClientGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientGroupService(db)
    return await service.update(group_id, group_data)


@router.delete("/groups/{group_id}", response_model=MessageResponse)
async def delete_client_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientGroupService(db)
    await service.delete(group_id)
    return MessageResponse(message="Client group deleted successfully")
