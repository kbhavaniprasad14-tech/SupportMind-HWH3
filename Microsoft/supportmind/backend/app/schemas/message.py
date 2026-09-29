from datetime import datetime

from pydantic import BaseModel


class MessageCreate(BaseModel):
    customer_id: int
    sender_type: str
    content: str


class MessageRead(MessageCreate):
    id: int
    ticket_id: int
    created_at: datetime
