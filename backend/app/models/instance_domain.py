from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class InstanceDomain(Base):
    __tablename__ = "instance_domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, index=True)

    # Full custom domain (e.g. "acme.com"). Bare mail to any address @domain
    # routes to the owning instance once the domain is verified (MX points here).
    domain = Column(String(255), unique=True, nullable=False, index=True)

    # Verified == the domain's MX record points to our mail host (mail reaches us)
    is_verified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)

    # Relationships
    instance = relationship("Instance", back_populates="domains")

    __table_args__ = (
        Index('idx_instance_domain_lookup', 'domain'),
    )

    def __repr__(self):
        return f"<InstanceDomain(id={self.id}, domain={self.domain}, verified={self.is_verified})>"
