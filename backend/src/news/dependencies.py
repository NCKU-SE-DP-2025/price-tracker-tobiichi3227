from fastapi import Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.news.service import AIService, NewsService


def get_news_service(db: Session = Depends(get_db), ai_service=None) -> NewsService:
    if ai_service is None:
        from src.news.service import ai_service

        return NewsService(db, ai_service)
    return NewsService(db, ai_service)


def get_ai_service() -> AIService:
    from src.news.service import ai_service

    return ai_service
