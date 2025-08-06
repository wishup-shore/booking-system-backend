from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class ClientGroupBase(BaseModel):
    name: str


class ClientGroupCreate(ClientGroupBase):
    pass


class ClientGroupUpdate(BaseModel):
    name: Optional[str] = None


class ClientGroup(ClientGroupBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ClientBase(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None  # {"vk": "link", "instagram": "link"}
    car_numbers: Optional[List[str]] = None  # ["A123BC78", "B456DE99"]
    photo_url: Optional[str] = None
    rating: Optional[float] = 0.0
    comments: Optional[str] = None
    group_id: Optional[int] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    car_numbers: Optional[List[str]] = None
    photo_url: Optional[str] = None
    rating: Optional[float] = None
    comments: Optional[str] = None
    group_id: Optional[int] = None


class Client(ClientBase):
    id: int
    created_at: datetime
    group: Optional[ClientGroup] = None

    class Config:
        from_attributes = True


class ClientWithStats(Client):
    """Client model with additional statistics"""

    visits_count: int = 0
    total_spent: float = 0.0
