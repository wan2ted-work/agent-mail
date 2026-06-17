from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class InstanceKey(Base):
    __tablename__ = "instance_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, index=True)

    # Unique key used in email address (e.g., "myproject" in wan2ted@myproject.mypm.cloud)
    key = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    instance = relationship("Instance", back_populates="keys")

    __table_args__ = (
        Index('idx_instance_key_lookup', 'key'),
    )

    def __repr__(self):
        return f"<InstanceKey(id={self.id}, key={self.key}, instance_id={self.instance_id})>"
