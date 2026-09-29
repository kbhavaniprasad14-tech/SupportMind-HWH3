from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.models.ticket import Ticket
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.routes.auth import get_current_user
from app.services.hindsight import HindsightService

router = APIRouter(prefix='/api/customers', tags=['customers'])


@router.get('', response_model=list[CustomerRead])
def list_customers(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Customer).all()


@router.post('', response_model=CustomerRead)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get('/{customer_id}', response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    return customer


@router.get('/{customer_id}/tickets')
def get_customer_tickets(customer_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    tickets = db.query(Ticket).filter(Ticket.customer_id == customer_id).all()
    return tickets


@router.get('/{customer_id}/memory')
def get_customer_memory(
    customer_id: int,
    query: str = Query(default='relevant previous support issues, troubleshooting steps, successful fixes, failed attempts, environment details, and customer preferences'),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    hindsight = HindsightService(db)
    memories = hindsight.recall(customer_id=customer_id, query=query)
    return {
        'customer_id': customer.id,
        'customer': {
            'id': customer.id,
            'external_customer_id': customer.external_customer_id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'company': customer.company,
            'status': customer.status,
            'created_at': customer.created_at,
            'last_interaction_at': customer.last_interaction_at,
        },
        'memory_count': len(memories),
        'memories': memories,
        'hindsight_available': hindsight.last_recall_available,
    }
