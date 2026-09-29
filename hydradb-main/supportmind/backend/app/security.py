from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False


def create_access_token(user_id: int, email: str, role: str):
    if not settings.JWT_SECRET:
        raise RuntimeError('JWT signing is not configured')
    payload = {
        'sub': str(user_id),
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm='HS256')


def decode_access_token(token: str):
    if not settings.JWT_SECRET:
        raise ValueError('JWT signing is not configured')
    return jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
