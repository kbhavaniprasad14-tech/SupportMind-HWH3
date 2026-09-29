from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class AnalyticsEvent(Base):
    __tablename__ = 'analytics_events'

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=True, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=True, index=True)
    event_type = Column(String(100), nullable=False)
    metadata_json = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
