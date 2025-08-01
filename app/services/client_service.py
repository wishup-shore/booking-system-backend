from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.models.client import Client, ClientGroup
from app.schemas.client import (
    ClientCreate,
    ClientUpdate,
    ClientWithStats,
    ClientGroupCreate,
    ClientGroupUpdate,
)
from app.core.service_utils import ensure_exists, ensure_no_related_records
from app.core.exceptions import ValidationError


class ClientGroupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[ClientGroup]:
        stmt = select(ClientGroup)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, group_id: int) -> Optional[ClientGroup]:
        stmt = select(ClientGroup).where(ClientGroup.id == group_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, group_data: ClientGroupCreate) -> ClientGroup:
        db_group = ClientGroup(**group_data.model_dump())
        self.db.add(db_group)
        await self.db.commit()
        await self.db.refresh(db_group)
        return db_group

    async def update(self, group_id: int, group_data: ClientGroupUpdate) -> ClientGroup:
        db_group = await self.get_by_id(group_id)
        db_group = ensure_exists(db_group, "Client group", group_id)

        update_data = group_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_group, field, value)

        await self.db.commit()
        await self.db.refresh(db_group)
        return db_group

    async def delete(self, group_id: int) -> bool:
        db_group = await self.get_by_id(group_id)
        db_group = ensure_exists(db_group, "Client group", group_id)

        # Check if group has clients
        clients_count_stmt = select(func.count(Client.id)).where(
            Client.group_id == group_id
        )
        clients_count_result = await self.db.execute(clients_count_stmt)
        clients_count = clients_count_result.scalar()

        ensure_no_related_records(clients_count or 0, "Client group", "clients")

        await self.db.delete(db_group)
        await self.db.commit()
        return True


class ClientService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Client]:
        stmt = select(Client).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, client_id: int) -> Optional[Client]:
        stmt = select(Client).where(Client.id == client_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search_clients(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> List[Client]:
        """Search clients by name, phone, or email"""
        if not query:
            return await self.get_all(skip, limit)

        search_filter = or_(
            func.lower(Client.first_name).contains(query.lower()),
            func.lower(Client.last_name).contains(query.lower()),
            Client.phone.contains(query),
            func.lower(Client.email).contains(query.lower()),
        )

        stmt = select(Client).where(search_filter).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_phone(self, phone: str) -> Optional[Client]:
        stmt = select(Client).where(Client.phone == phone)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Client]:
        stmt = select(Client).where(Client.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, client_data: ClientCreate) -> Client:
        # Check for duplicate phone/email if provided
        if client_data.phone and await self.get_by_phone(client_data.phone):
            raise ValidationError("Client with this phone number already exists")

        if client_data.email and await self.get_by_email(client_data.email):
            raise ValidationError("Client with this email already exists")

        db_client = Client(**client_data.model_dump())
        self.db.add(db_client)
        await self.db.commit()
        await self.db.refresh(db_client)
        return db_client

    async def update(self, client_id: int, client_data: ClientUpdate) -> Client:
        db_client = await self.get_by_id(client_id)
        db_client = ensure_exists(db_client, "Client", client_id)

        # Check for duplicate phone/email if being updated
        if client_data.phone and client_data.phone != db_client.phone:
            existing_client = await self.get_by_phone(client_data.phone)
            if existing_client and existing_client.id != client_id:
                raise ValidationError(
                    "Another client with this phone number already exists"
                )

        if client_data.email and client_data.email != db_client.email:
            existing_client = await self.get_by_email(client_data.email)
            if existing_client and existing_client.id != client_id:
                raise ValidationError("Another client with this email already exists")

        update_data = client_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_client, field, value)

        await self.db.commit()
        await self.db.refresh(db_client)
        return db_client

    async def delete(self, client_id: int) -> bool:
        db_client = await self.get_by_id(client_id)
        db_client = ensure_exists(db_client, "Client", client_id)

        await self.db.delete(db_client)
        await self.db.commit()
        return True

    async def get_client_stats(self, client_id: int) -> ClientWithStats:
        """Get client with basic statistics"""
        db_client = await self.get_by_id(client_id)
        db_client = ensure_exists(db_client, "Client", client_id)

        # For now, return zero stats since we don't have bookings yet
        # This will be updated in iteration 3 when booking system is implemented
        client_with_stats = ClientWithStats.model_validate(db_client)
        client_with_stats.visits_count = 0
        client_with_stats.total_spent = 0.0

        return client_with_stats
