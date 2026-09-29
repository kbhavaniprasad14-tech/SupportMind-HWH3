from app.models.customer import Customer
from app.models.user import User
from app.config import get_settings
from app.security import hash_password


def seed_demo_data(db):
    settings = get_settings()
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD and not db.query(User).filter(User.email == settings.ADMIN_EMAIL).first():
        db.add(User(
            name='Support Admin',
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role='ADMIN',
        ))

    # seed demo customers
    customers = [
        {
            'external_customer_id': 'rahul-001',
            'name': 'Rahul Kumar',
            'email': 'rahul@cloudbridge.io',
            'phone': '+91 98765 43210',
            'company': 'CloudBridge',
            'status': 'ACTIVE',
        },
        {
            'external_customer_id': 'priya-002',
            'name': 'Priya Sharma',
            'email': 'priya@northstarcommerce.com',
            'phone': '+91 98222 33445',
            'company': 'Northstar Commerce',
            'status': 'ACTIVE',
        },
        {
            'external_customer_id': 'arjun-003',
            'name': 'Arjun Reddy',
            'email': 'arjun@launchops.dev',
            'phone': '+91 99888 77661',
            'company': 'LaunchOps',
            'status': 'ACTIVE',
        },
    ]

    for data in customers:
        existing = db.query(Customer).filter(Customer.external_customer_id == data['external_customer_id']).first()
        if not existing:
            db.add(Customer(**data))

    db.commit()
