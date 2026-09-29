from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    customer_id: int
    title: str
    category: str = 'GENERAL'
    priority: str = 'MEDIUM'


class TicketRead(TicketCreate):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
