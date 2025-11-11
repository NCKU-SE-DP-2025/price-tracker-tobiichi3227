# backend/src/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///news_database.db"
    JWT_SECRET: str = "1892dhianiandowqd0n"
    OPENAI_API_KEY: str = "xxx"
    SENTRY_DSN: str = "https://4001ffe917ccb261aa0e0c34026dc343@o4505702629834752.ingest.us.sentry.io/4507694792704000"
    CORS_ORIGINS: list[str] = ["http://localhost:8080"]
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 30


settings = Settings()
