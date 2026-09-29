from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True, index=True)
    external_customer_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    status = Column(String(50), default='ACTIVE')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_interaction_at = Column(DateTime(timezone=True), nullable=True)
