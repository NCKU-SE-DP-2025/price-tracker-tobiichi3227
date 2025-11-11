from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.auth.config import auth_settings


class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def authenticate_user(self, db, username: str, password: str):
        from src.auth.models import User

        user = db.query(User).filter(User.username == username).first()
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_token(self, username: str, expire_minutes: int = None) -> str:
        expire = datetime.utcnow() + timedelta(
            minutes=expire_minutes or auth_settings.JWT_EXP
        )
        payload = {"sub": username, "exp": expire}
        return jwt.encode(
            payload, auth_settings.JWT_SECRET, algorithm=auth_settings.JWT_ALGORITHM
        )

    def verify_token(self, token: str) -> str:
        try:
            payload = jwt.decode(
                token,
                auth_settings.JWT_SECRET,
                algorithms=[auth_settings.JWT_ALGORITHM],
            )
            username = payload.get("sub")
            if not username:
                raise ValueError("Invalid token")
            return username
        except JWTError as exc:
            raise ValueError("Invalid token") from exc
