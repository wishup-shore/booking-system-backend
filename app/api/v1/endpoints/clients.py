from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

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
from app.services.client_service import ClientService, ClientGroupService

router = APIRouter()


def require_staff_role(current_user: User = Depends(get_active_user)):
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff role required")
    return current_user


# Client endpoints
@router.get("/", response_model=List[Client])
def get_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Search by name, phone, or email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    service = ClientService(db)
    if search:
        return service.search_clients(search, skip, limit)
    return service.get_all(skip, limit)


@router.post("/", response_model=Client)
def create_client(
    client_data: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientService(db)
    return service.create(client_data)


@router.get("/{client_id}", response_model=Client)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    service = ClientService(db)
    client = service.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=Client)
def update_client(
    client_id: int,
    client_data: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientService(db)
    return service.update(client_id, client_data)


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientService(db)
    service.delete(client_id)
    return {"message": "Client deleted successfully"}


@router.get("/{client_id}/stats", response_model=ClientWithStats)
def get_client_stats(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    service = ClientService(db)
    return service.get_client_stats(client_id)


# Client Group endpoints
@router.get("/groups/", response_model=List[ClientGroup])
def get_client_groups(
    db: Session = Depends(get_db), current_user: User = Depends(get_active_user)
):
    service = ClientGroupService(db)
    return service.get_all()


@router.post("/groups/", response_model=ClientGroup)
def create_client_group(
    group_data: ClientGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientGroupService(db)
    return service.create(group_data)


@router.get("/groups/{group_id}", response_model=ClientGroup)
def get_client_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    service = ClientGroupService(db)
    group = service.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Client group not found")
    return group


@router.put("/groups/{group_id}", response_model=ClientGroup)
def update_client_group(
    group_id: int,
    group_data: ClientGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientGroupService(db)
    return service.update(group_id, group_data)


@router.delete("/groups/{group_id}")
def delete_client_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    service = ClientGroupService(db)
    service.delete(group_id)
    return {"message": "Client group deleted successfully"}
