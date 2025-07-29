from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from fastapi import HTTPException, status

from app.models.client import Client, ClientGroup
from app.schemas.client import (
    ClientCreate, ClientUpdate, ClientWithStats,
    ClientGroupCreate, ClientGroupUpdate
)


class ClientGroupService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self) -> List[ClientGroup]:
        return self.db.query(ClientGroup).all()
    
    def get_by_id(self, group_id: int) -> Optional[ClientGroup]:
        return self.db.query(ClientGroup).filter(ClientGroup.id == group_id).first()
    
    def create(self, group_data: ClientGroupCreate) -> ClientGroup:
        db_group = ClientGroup(**group_data.model_dump())
        self.db.add(db_group)
        self.db.commit()
        self.db.refresh(db_group)
        return db_group
    
    def update(self, group_id: int, group_data: ClientGroupUpdate) -> ClientGroup:
        db_group = self.get_by_id(group_id)
        if not db_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client group not found"
            )
        
        update_data = group_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_group, field, value)
        
        self.db.commit()
        self.db.refresh(db_group)
        return db_group
    
    def delete(self, group_id: int) -> bool:
        db_group = self.get_by_id(group_id)
        if not db_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client group not found"
            )
        
        # Check if group has clients
        clients_count = self.db.query(Client).filter(Client.group_id == group_id).count()
        if clients_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete group with existing clients"
            )
        
        self.db.delete(db_group)
        self.db.commit()
        return True


class ClientService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Client]:
        return self.db.query(Client).offset(skip).limit(limit).all()
    
    def get_by_id(self, client_id: int) -> Optional[Client]:
        return self.db.query(Client).filter(Client.id == client_id).first()
    
    def search_clients(self, query: str, skip: int = 0, limit: int = 100) -> List[Client]:
        """Search clients by name, phone, or email"""
        if not query:
            return self.get_all(skip, limit)
        
        search_filter = or_(
            func.lower(Client.first_name).contains(query.lower()),
            func.lower(Client.last_name).contains(query.lower()),
            Client.phone.contains(query),
            func.lower(Client.email).contains(query.lower())
        )
        
        return self.db.query(Client).filter(search_filter).offset(skip).limit(limit).all()
    
    def get_by_phone(self, phone: str) -> Optional[Client]:
        return self.db.query(Client).filter(Client.phone == phone).first()
    
    def get_by_email(self, email: str) -> Optional[Client]:
        return self.db.query(Client).filter(Client.email == email).first()
    
    def create(self, client_data: ClientCreate) -> Client:
        # Check for duplicate phone/email if provided
        if client_data.phone and self.get_by_phone(client_data.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client with this phone number already exists"
            )
        
        if client_data.email and self.get_by_email(client_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client with this email already exists"
            )
        
        db_client = Client(**client_data.model_dump())
        self.db.add(db_client)
        self.db.commit()
        self.db.refresh(db_client)
        return db_client
    
    def update(self, client_id: int, client_data: ClientUpdate) -> Client:
        db_client = self.get_by_id(client_id)
        if not db_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        # Check for duplicate phone/email if being updated
        if client_data.phone and client_data.phone != db_client.phone:
            existing_client = self.get_by_phone(client_data.phone)
            if existing_client and existing_client.id != client_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another client with this phone number already exists"
                )
        
        if client_data.email and client_data.email != db_client.email:
            existing_client = self.get_by_email(client_data.email)
            if existing_client and existing_client.id != client_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another client with this email already exists"
                )
        
        update_data = client_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_client, field, value)
        
        self.db.commit()
        self.db.refresh(db_client)
        return db_client
    
    def delete(self, client_id: int) -> bool:
        db_client = self.get_by_id(client_id)
        if not db_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        self.db.delete(db_client)
        self.db.commit()
        return True
    
    def get_client_stats(self, client_id: int) -> ClientWithStats:
        """Get client with basic statistics"""
        db_client = self.get_by_id(client_id)
        if not db_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        # For now, return zero stats since we don't have bookings yet
        # This will be updated in iteration 3 when booking system is implemented
        client_with_stats = ClientWithStats.model_validate(db_client)
        client_with_stats.visits_count = 0
        client_with_stats.total_spent = 0.0
        
        return client_with_stats