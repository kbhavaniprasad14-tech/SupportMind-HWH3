import json
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analytics_event import AnalyticsEvent
from app.models.customer import Customer
from app.models.memory_event import MemoryEvent
from app.models.message import Message
from app.models.ticket import Ticket
from app.routes.auth import get_current_user

router = APIRouter(prefix='/api', tags=['analytics'])


def _dashboard_data(db: Session):
    customers = db.query(Customer).count()
    tickets = db.query(Ticket).all()
    memory_events = db.query(MemoryEvent).all()
    successful_retains = 0
    for event in memory_events:
        try:
            successful_retains += bool(json.loads(event.metadata_json or '{}').get('hindsight_success'))
        except (TypeError, ValueError):
            continue

    status_counts = Counter(ticket.status for ticket in tickets)
    priority_counts = Counter(ticket.priority for ticket in tickets)
    monthly_counts = Counter(
        ticket.created_at.strftime('%Y-%m')
        for ticket in tickets
        if ticket.created_at
    )
    return {
        'total_customers': customers,
        'active_customers': db.query(Customer).filter(Customer.status == 'ACTIVE').count(),
        'total_tickets': len(tickets),
        'open_tickets': status_counts.get('OPEN', 0),
        'pending_tickets': status_counts.get('PENDING', 0),
        'resolved_tickets': status_counts.get('RESOLVED', 0),
        'total_memory_events': len(memory_events),
        'hindsight_retention_count': successful_retains,
        'hindsight_retrieval_count': db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == 'HINDSIGHT_RETRIEVAL'
        ).count(),
        'agent_interactions': db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == 'AGENT_INTERACTION'
        ).count(),
        'average_tickets_per_customer': round(len(tickets) / customers, 2) if customers else None,
        'tickets_by_status': dict(status_counts),
        'tickets_by_priority': dict(priority_counts),
        'tickets_over_time': [
            {'month': month, 'count': count}
            for month, count in sorted(monthly_counts.items())
        ],
    }


@router.get('/analytics/dashboard')
def dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _dashboard_data(db)


@router.get('/analytics')
def analytics(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _dashboard_data(db)
