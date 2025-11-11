from datetime import timedelta

from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    JWT_ALGORITHM: str = "HS256"
    JWT_SECRET: str = "1892dhianiandowqd0n"
    JWT_EXP: int = 30  # minutes

    REFRESH_TOKEN_KEY: str = "refresh_token"
    REFRESH_TOKEN_EXP: timedelta = timedelta(days=30)
    SECURE_COOKIES: bool = True


auth_settings = AuthConfig()
