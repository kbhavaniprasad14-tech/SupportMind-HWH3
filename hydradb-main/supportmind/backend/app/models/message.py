from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False, index=True)
    sender_type = Column(String(50), nullable=False)  # CUSTOMER or AGENT
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
