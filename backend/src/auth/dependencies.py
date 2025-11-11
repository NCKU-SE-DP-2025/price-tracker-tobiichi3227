from http import HTTPStatus

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.auth.constants import INVALID_TOKEN, USER_NOT_FOUND
from src.auth.models import User
from src.auth.service import AuthService
from src.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")
auth_service = AuthService()


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    try:
        username = auth_service.verify_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED, detail=INVALID_TOKEN
        ) from exc
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=USER_NOT_FOUND)
    return user
