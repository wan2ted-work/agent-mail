from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


# Instance Key schemas
class InstanceKeyCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=255, description="Public instance key (used in email address)")


class InstanceKeyResponse(BaseModel):
    id: UUID
    instance_id: UUID
    key: str
    created_at: datetime

    class Config:
        from_attributes = True


# Instance Domain schemas
class InstanceDomainCreate(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255, description="Full custom domain, e.g. acme.com")


class InstanceDomainResponse(BaseModel):
    id: UUID
    instance_id: UUID
    domain: str
    is_verified: bool
    created_at: datetime
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Instance schemas
class InstanceCreate(BaseModel):
    secret: Optional[UUID] = Field(None, description="Secret UUID for API access (auto-generated if not provided)")
    description: Optional[str] = Field(None, max_length=500, description="Instance description")


class InstanceUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class InstanceResponse(BaseModel):
    id: UUID
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    keys: List['InstanceKeyResponse'] = []
    domains: List['InstanceDomainResponse'] = []

    class Config:
        from_attributes = True


class InstanceWithEmailCount(InstanceResponse):
    email_count: int


# Email schemas
class EmailResponse(BaseModel):
    id: UUID
    instance_id: Optional[UUID]
    extracted_key: str
    message_id: str
    from_email: str
    from_name: Optional[str]
    to_email: str
    subject: Optional[str]
    body_text: Optional[str]
    body_html: Optional[str]
    filename: str
    received_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class EmailListResponse(BaseModel):
    id: UUID
    from_email: str
    from_name: Optional[str]
    to_email: str
    extracted_key: str
    subject: Optional[str]
    received_at: datetime
    has_instance: bool

    class Config:
        from_attributes = True


# Pagination
class PaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[Any]


# General responses
class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
