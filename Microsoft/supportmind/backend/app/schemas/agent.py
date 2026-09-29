from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    customer_id: int
    ticket_id: Optional[int] = None
    message: str
    use_memory: bool = True


class ChatResponse(BaseModel):
    message: str
    memory_used: bool = False
    memory_count: int = 0
    memory_references: list[str] = []
    memory_enabled: bool = True
    memory_available: bool = False
    memory_retained: bool = False
    ticket_id: Optional[int] = None
    timestamp: datetime
