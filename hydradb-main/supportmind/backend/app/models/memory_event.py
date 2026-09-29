from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class MemoryEvent(Base):
    __tablename__ = 'memory_events'

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)
    hindsight_bank_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata_json = Column(String, nullable=True)
