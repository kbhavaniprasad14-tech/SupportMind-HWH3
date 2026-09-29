from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, default='GENERAL')
    priority = Column(String(50), nullable=False, default='MEDIUM')
    status = Column(String(50), nullable=False, default='OPEN')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship('Customer')
