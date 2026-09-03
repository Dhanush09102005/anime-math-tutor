"""
FastAPI dependency that resolves the current user from the auth cookie.

Use as `current_user: User = Depends(get_current_user)` on any route that
requires auth — every route under routes/session.py, problem.py, submit.py,
chat.py should have this now, since sessions are user-scoped.
"""

import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User
from auth.security import decode_access_token

COOKIE_NAME = "access_token"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user
