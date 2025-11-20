from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user
from src.database import get_db
from src.news.dependencies import get_news_service
from src.news.schemas import (
    NewsArticleResponse,
    NewsSummaryRequest,
    NewsSummaryResponse,
    PromptRequest,
)
from src.news.service import NewsService

router = APIRouter()


@router.get("/news", response_model=list[NewsArticleResponse])
def get_news(
    db: Session = Depends(get_db), service: NewsService = Depends(get_news_service)
):
    articles = service.get_all_articles()
    return [
        NewsArticleResponse.model_validate(
            article,
            upvote_cnt=service.count_upvote(article.id),
            is_upvoted=False,
        )
        for article in articles
    ]


@router.get("/user_news", response_model=list[NewsArticleResponse])
def get_user_news(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    service: NewsService = Depends(get_news_service),
):
    articles = service.get_all_articles()
    return [
        NewsArticleResponse.model_validate(
            article,
            upvote_cnt=service.count_upvote(article.id),
            is_upvoted=service.is_upvoted_by_user(article.id, current_user.id),
        )
        for article in articles
    ]


@router.post("/search_news", response_model=list[dict])
def search_news(
    prompt_request: PromptRequest,
    service: NewsService = Depends(get_news_service),
):
    results = service.search_by_prompt(prompt_request.prompt)
    return results


@router.post("/news_summary", response_model=NewsSummaryResponse)
def news_summary(
    payload: NewsSummaryRequest,
    service: NewsService = Depends(get_news_service),
):
    summary = service.ai_service.summarize_news(payload.content)
    return NewsSummaryResponse(summary=summary["影響"], reason=summary["原因"])


@router.post("/{article_id}/upvote")
def upvote_news(
    article_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    service: NewsService = Depends(get_news_service),
):
    upvoted = service.toggle_upvote(article_id, current_user.id)
    return {"message": "Article upvoted" if upvoted else "Upvote removed"}
