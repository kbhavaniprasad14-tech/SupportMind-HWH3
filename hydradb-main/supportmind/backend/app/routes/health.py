from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal

router = APIRouter(prefix='/api/health', tags=['health'])


@router.get('')
def health_check():
    settings = get_settings()
    try:
        db = SessionLocal()
        db.execute(text('SELECT 1'))
        db.close()
        database_status = 'ok'
    except Exception:
        database_status = 'error'

    status = {
        'backend': 'ok',
        'database': database_status,
        'hindsight': 'configured' if settings.HINDSIGHT_URL and settings.HINDSIGHT_API_KEY else 'not_configured',
        'llm': 'configured' if settings.GROQ_API_KEY else 'not_configured',
    }
    return status
