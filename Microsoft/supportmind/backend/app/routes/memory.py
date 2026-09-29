import json

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.routes.auth import get_current_user
from app.services.hindsight import HindsightService


router = APIRouter(prefix='/api/memory', tags=['memory'])


class RecallRequest(BaseModel):
    query: str = 'previous support issues, troubleshooting steps, successful fixes, failed attempts, environment details, and customer preferences'


class RetainRequest(BaseModel):
    summary: str
    ticket_id: int | None = None
    event_type: str = 'MANUAL'


class ReflectRequest(BaseModel):
    query: str = 'important customer history, known issues, successful solutions, failed attempts, environment, and preferences'


@router.post('/{customer_id}/retain')
def retain(
    customer_id: int,
    payload: RetainRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not db.query(Customer.id).filter(Customer.id == customer_id).first():
        raise HTTPException(status_code=404, detail='Customer not found')
    hindsight = HindsightService(db)

    record = hindsight.retain(
        customer_id=customer_id,
        ticket_id=payload.ticket_id,
        event_type=payload.event_type,
        summary=payload.summary,
    )
    hindsight_saved = False
    if record and record.metadata_json:
        try:
            hindsight_saved = bool(json.loads(record.metadata_json).get('hindsight_success'))
        except (TypeError, ValueError):
            pass

    return {
        'status': 'retained' if hindsight_saved else 'not_retained',
        'customer_id': customer_id,
        'ticket_id': payload.ticket_id,
        'event_type': payload.event_type,
        'hindsight_saved': hindsight_saved,
        'local_event_saved': bool(record),
    }


@router.post('/{customer_id}/recall')
def recall(
    customer_id: int,
    payload: RecallRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not db.query(Customer.id).filter(Customer.id == customer_id).first():
        raise HTTPException(status_code=404, detail='Customer not found')
    hindsight = HindsightService(db)

    memories = hindsight.recall(
        customer_id=customer_id,
        query=payload.query,
    )

    return {
        'status': 'recalled',
        'customer_id': customer_id,
        'memory_count': len(memories),
        'memories': memories,
        'hindsight_available': hindsight.last_recall_available,
    }


@router.post('/{customer_id}/reflect')
def reflect(
    customer_id: int,
    payload: ReflectRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not db.query(Customer.id).filter(Customer.id == customer_id).first():
        raise HTTPException(status_code=404, detail='Customer not found')
    hindsight = HindsightService(db)

    memories = hindsight.recall(
        customer_id=customer_id,
        query=payload.query,
    )

    summary = hindsight.reflect(
        customer_id=customer_id,
        memories=memories,
    )

    return {
        'status': 'reflected',
        'customer_id': customer_id,
        'memory_count': len(memories),
        'summary': summary,
        'memories': memories,
        'hindsight_available': hindsight.last_recall_available,
    }