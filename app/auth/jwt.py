from datetime import datetime, timedelta

import jwt

from app.core.config import settings


ALGORITHM = "HS256"


def create_access_token(user_id: str, role: str, expires_minutes: int = 60) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
