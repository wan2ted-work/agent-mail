from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class Email(Base):
    __tablename__ = "emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("instances.id", ondelete="SET NULL"), nullable=True, index=True)

    # Extracted key from email address (e.g., "key" from wan2ted@key.mypm.cloud)
    extracted_key = Column(String(255), nullable=False, index=True)

    # Email headers
    message_id = Column(String(500), unique=True, nullable=False, index=True)
    from_email = Column(String(255), nullable=False, index=True)
    from_name = Column(String(255), nullable=True)
    to_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=True, index=True)

    # Email content
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)

    # Metadata
    raw_email = Column(Text, nullable=False)
    filename = Column(String(500), nullable=False)
    received_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    instance = relationship("Instance", back_populates="emails")

    __table_args__ = (
        Index('idx_instance_received', 'instance_id', 'received_at'),
        Index('idx_extracted_key', 'extracted_key'),
        Index('idx_from_email_search', 'from_email', postgresql_using='gin', postgresql_ops={'from_email': 'gin_trgm_ops'}),
        Index('idx_subject_search', 'subject', postgresql_using='gin', postgresql_ops={'subject': 'gin_trgm_ops'}),
    )

    def __repr__(self):
        return f"<Email(id={self.id}, from={self.from_email}, subject={self.subject})>"
