from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base


class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    social_links = Column(JSON, nullable=True)  # {"vk": "link", "instagram": "link", etc}
    car_numbers = Column(JSON, nullable=True)   # ["A123BC78", "B456DE99"]
    photo_url = Column(String, nullable=True)
    rating = Column(Float, nullable=True, default=0.0)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to client group
    group_id = Column(Integer, ForeignKey("client_groups.id"), nullable=True)
    group = relationship("ClientGroup", back_populates="clients")


class ClientGroup(Base):
    __tablename__ = "client_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "Семья Ивановых", "Компания друзей"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to clients
    clients = relationship("Client", back_populates="group")