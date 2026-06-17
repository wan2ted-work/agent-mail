from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class Instance(Base):
    __tablename__ = "instances"

    # id is the secret UUID - used for API access
    id = Column(UUID(as_uuid=True), primary_key=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    emails = relationship("Email", back_populates="instance")
    keys = relationship("InstanceKey", back_populates="instance", cascade="all, delete-orphan")
    domains = relationship("InstanceDomain", back_populates="instance", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Instance(id={self.id})>"
