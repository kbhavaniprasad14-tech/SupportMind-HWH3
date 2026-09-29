from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    external_customer_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None


class CustomerRead(CustomerCreate):
    id: int
    status: str
    created_at: datetime
    last_interaction_at: Optional[datetime] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
