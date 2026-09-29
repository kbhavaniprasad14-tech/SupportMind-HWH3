from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.models.analytics_event import AnalyticsEvent
from app.models.message import Message
from app.models.ticket import Ticket
from app.routes.auth import get_current_user
from app.schemas.agent import ChatRequest, ChatResponse
from app.services.llm import GroqProvider
from app.services.memory_service import MemoryService

router = APIRouter(prefix='/api/agent', tags=['agent'])


def _build_memory_summary(customer: Customer, ticket: Ticket | None, issue: str, recent_messages: list[Message]):
    details = [
        f"Customer: {customer.name}",
        f"Company: {customer.company or 'Not provided'}",
        f"Current issue: {issue}",
    ]
    if ticket:
        details.append(f"Ticket: {ticket.title} (priority={ticket.priority}, status={ticket.status})")

    if recent_messages:
        history = ' | '.join(
            f"{msg.sender_type.title()}: {msg.content}"
            for msg in recent_messages[-6:]
        )
        details.append(f"Recent conversation: {history}")

    return ' | '.join(details)


@router.post('/chat', response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')

    if payload.ticket_id is not None:
        ticket = db.query(Ticket).filter(Ticket.id == payload.ticket_id).first()
        if not ticket or ticket.customer_id != customer.id:
            raise HTTPException(status_code=404, detail='Ticket not found')
    else:
        ticket = Ticket(
            customer_id=customer.id,
            title=f"{customer.name} support conversation",
            category='GENERAL',
            priority='MEDIUM',
            status='OPEN',
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

    recent_messages = (
        db.query(Message)
        .filter(Message.customer_id == customer.id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )
    recent_messages = list(reversed(recent_messages))

    memory_summary = _build_memory_summary(customer, ticket, payload.message, recent_messages)
    db.add(Message(ticket_id=ticket.id, customer_id=customer.id, sender_type='CUSTOMER', content=payload.message))
    db.commit()

    memory_service = MemoryService(db)
    recall = memory_service.recall_context(customer.id, payload.message, ticket_id=ticket.id) if payload.use_memory else {
        'memories': [],
        'summary': 'Historical memory was not included for this request.',
        'hindsight_available': False,
    }
    memories = recall['memories']
    reflection = recall['summary']

    system_prompt = (
        'You are SupportMind, an AI customer-support agent. Remember the full customer context across chats and tickets. '
        'Always capture and retain the customer name, company, issue description, device/environment, troubleshooting steps attempted, '
        'failed solutions, successful fixes, escalation notes, and customer preferences. Never invent history. '
        'Use prior memory to avoid re-asking known facts, but do not expose another customer\'s data. '
        'When a solution has previously worked, prefer it over repeating failed steps. '
        'Keep the answer concise but complete and grounded in the remembered facts.'
    )
    user_prompt = (
        f"CURRENT CUSTOMER: {customer.name}\n"
        f"CUSTOMER COMPANY: {customer.company or 'Not provided'}\n"
        f"CURRENT ISSUE: {payload.message}\n"
        f"CURRENT TICKET: {ticket.title}\n"
        f"RECENT CONVERSATION: {' | '.join(f'{m.sender_type.title()}: {m.content}' for m in recent_messages[-5:]) if recent_messages else 'No prior conversation'}\n"
        f"RELEVANT CUSTOMER MEMORY: {memories}\n"
        f"REFLECTION: {reflection}\n"
        'Use the stored customer context to craft a helpful support answer and maintain the full memory of this case.'
    )

    llm = GroqProvider()
    try:
        response_text = llm.generate(system_prompt, user_prompt)
    except RuntimeError as exc:
        record = memory_service.retain_context(customer.id, ticket.id, 'CHAT', memory_summary)
        retained = False
        if record and record.metadata_json:
            try:
                retained = bool(json.loads(record.metadata_json).get('hindsight_success'))
            except (TypeError, ValueError):
                pass
        return JSONResponse(
            status_code=503,
            content={
                'detail': 'The AI response is temporarily unavailable. Retrieved Hindsight records, if any, are included below.',
                'ticket_id': ticket.id,
                'memory_status': {
                    'available': recall.get('hindsight_available', False),
                    'used': bool(memories),
                    'count': len(memories),
                    'references': [item.get('summary', 'memory') for item in memories[:4]],
                    'memories': memories,
                    'retained': retained,
                },
            },
        )

    db.add(Message(ticket_id=ticket.id, customer_id=customer.id, sender_type='AGENT', content=response_text))
    db.commit()

    record = memory_service.retain_context(customer.id, ticket.id, 'CHAT', memory_summary)
    db.add(AnalyticsEvent(
        customer_id=customer.id,
        ticket_id=ticket.id,
        event_type='AGENT_INTERACTION',
    ))
    customer.last_interaction_at = datetime.now(timezone.utc)
    db.commit()
    retained = False
    if record and record.metadata_json:
        try:
            retained = bool(json.loads(record.metadata_json).get('hindsight_success'))
        except (TypeError, ValueError):
            pass

    return ChatResponse(
        message=response_text,
        memory_used=bool(memories),
        memory_count=len(memories),
        memory_references=[m.get('summary', 'memory') for m in memories[:4]],
        memory_enabled=payload.use_memory,
        memory_available=recall.get('hindsight_available', False),
        memory_retained=retained,
        ticket_id=ticket.id,
        timestamp=datetime.now(timezone.utc),
    )
