from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routes import agent, analytics, auth, customers, health, memory, tickets
from app.services.seed import seed_demo_data

settings = get_settings()

app = FastAPI(title='SupportMind', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:5174',
        'http://127.0.0.1:5174',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    seed_demo_data(db)

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(tickets.router)
app.include_router(agent.router)
app.include_router(memory.router)
app.include_router(analytics.router)
app.include_router(health.router)


@app.get('/')
def read_root():
    return {'app': 'SupportMind', 'status': 'running'}
