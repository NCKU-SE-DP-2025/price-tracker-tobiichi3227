from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user
from src.auth.exceptions import InvalidCredentials, UserAlreadyExists
from src.auth.models import User
from src.auth.schemas import TokenResponse, UserAuthRequest, UserResponse
from src.auth.service import AuthService
from src.database import get_db

router = APIRouter()

auth_service = AuthService()


@router.post("/register", response_model=UserResponse)
def register(user: UserAuthRequest, db: Session = Depends(get_db)):
    is_existing = db.query(User).filter(User.username == user.username).first()
    if is_existing:
        raise UserAlreadyExists()
    hashed_password = auth_service.hash_password(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserResponse.model_validate(db_user)


@router.post("/login", response_model=TokenResponse)
def login(user: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_obj = auth_service.authenticate_user(db, user.username, user.password)
    if not user_obj:
        raise InvalidCredentials()
    access_token = auth_service.create_token(username=user_obj.username)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
