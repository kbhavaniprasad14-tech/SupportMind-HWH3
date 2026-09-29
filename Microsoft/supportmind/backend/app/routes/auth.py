from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix='/api/auth', tags=['auth'])
security = HTTPBearer()


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    from app.security import decode_access_token

    try:
        payload = decode_access_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token') from exc

    user = db.query(User).filter(User.id == int(payload['sub'])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    return user


@router.post('/login')
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    if not get_settings().JWT_SECRET:
        raise HTTPException(status_code=503, detail='Authentication is not configured')
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')

    token = create_access_token(user.id, user.email, user.role)
    return {
        'access_token': token,
        'token_type': 'bearer',
        'user': {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role},
    }


@router.post('/logout')
def logout():
    return {'message': 'Logged out'}
