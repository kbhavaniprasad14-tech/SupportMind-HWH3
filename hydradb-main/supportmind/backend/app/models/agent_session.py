from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func

from app.database import Base


class AgentSession(Base):
    __tablename__ = 'agent_sessions'

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
