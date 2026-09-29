from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.models.message import Message
from app.models.ticket import Ticket
from app.schemas.message import MessageCreate, MessageRead
from app.schemas.ticket import TicketCreate, TicketRead, TicketUpdate
from app.routes.auth import get_current_user

router = APIRouter(prefix='/api/tickets', tags=['tickets'])


@router.get('', response_model=list[TicketRead])
def list_tickets(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = db.query(Ticket)
    if status:
        query = query.filter(Ticket.status == status.upper())
    if priority:
        query = query.filter(Ticket.priority == priority.upper())
    if customer_id is not None:
        query = query.filter(Ticket.customer_id == customer_id)
    return query.order_by(Ticket.created_at.desc()).all()


@router.post('', response_model=TicketRead)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not db.query(Customer.id).filter(Customer.id == payload.customer_id).first():
        raise HTTPException(status_code=404, detail='Customer not found')
    ticket = Ticket(**payload.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get('/{ticket_id}', response_model=TicketRead)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    return ticket


@router.patch('/{ticket_id}', response_model=TicketRead)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    if payload.status is not None:
        ticket.resolved_at = datetime.now(timezone.utc) if payload.status.upper() == 'RESOLVED' else None
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get('/{ticket_id}/messages', response_model=list[MessageRead])
def get_messages(ticket_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not db.query(Ticket.id).filter(Ticket.id == ticket_id).first():
        raise HTTPException(status_code=404, detail='Ticket not found')
    return db.query(Message).filter(Message.ticket_id == ticket_id).order_by(Message.created_at.asc()).all()


@router.post('/{ticket_id}/messages', response_model=MessageRead)
def create_message(ticket_id: int, payload: MessageCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    if payload.customer_id != ticket.customer_id:
        raise HTTPException(status_code=400, detail='Customer does not own this ticket')
    message = Message(ticket_id=ticket_id, **payload.model_dump())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
