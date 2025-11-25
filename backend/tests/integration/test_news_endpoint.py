from unittest.mock import Mock

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from src.auth.models import User
from src.database import Base, get_db
from src.main import app
from src.news.dependencies import get_news_service
from src.news.models import NewsArticle
from src.news.schemas import NewsSummaryRequest
from src.news.service import AIService, NewsService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "1892dhianiandowqd0n"
ALGORITHM = "HS256"
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_session_opener():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_session_opener
client = TestClient(app)


@pytest.fixture(scope="module")
def clear_users():
    with next(override_session_opener()) as db:
        db.query(User).delete()
        db.commit()


@pytest.fixture(scope="module")
def test_user(clear_users):
    hashed_password = pwd_context.hash("testpassword")

    with next(override_session_opener()) as db:
        user = User(username="testuser", hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture(scope="module")
def test_token(test_user):
    access_token = jwt.encode({"sub": test_user.username}, SECRET_KEY, algorithm=ALGORITHM)
    return access_token


@pytest.fixture(scope="function")
def test_articles():
    with next(override_session_opener()) as db:
        db.query(NewsArticle).delete()
        db.commit()

        article_1 = NewsArticle(
            url="https://example.com/test-news-1",
            title="Test News 1",
            content="This is test content 1",
            time="2024-01-01",
            summary="Test summary 1",
            reason="Test reason 1",
        )
        article_2 = NewsArticle(
            url="https://example.com/test-news-2",
            title="Test News 2",
            content="This is test content 2",
            time="2024-01-02",
            summary="Test summary 2",
            reason="Test reason 2",
        )
        db.add_all([article_1, article_2])
        db.commit()
        db.refresh(article_1)
        db.refresh(article_2)

        return [article_1, article_2]


@pytest.fixture(scope="function")
def test_user_and_articles(test_user, test_articles):
    return test_user, test_articles


def test_read_news(test_articles):
    response = client.get("/api/v1/news/news")
    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == 2
    assert json_response[0]["title"] == "Test News 2"
    assert json_response[1]["title"] == "Test News 1"


def test_read_user_news(test_user, test_token, test_articles):
    headers = {"Authorization": f"Bearer {test_token}"}
    response = client.get("/api/v1/news/user_news", headers=headers)
    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == 2
    assert json_response[0]["title"] == "Test News 2"
    assert json_response[0]["is_upvoted"] is False
    assert json_response[1]["title"] == "Test News 1"
    assert json_response[1]["is_upvoted"] is False


def mock_openai(mocker, return_content):
    mock_openai_client = mocker.patch("src.news.service.OpenAI")

    mock_message = Mock()
    mock_message.content = return_content

    mock_choice = Mock()
    mock_choice.message = mock_message

    mock_completion = Mock()
    mock_completion.choices = [mock_choice]

    mock_openai_client.return_value.chat.completions.create.return_value = mock_completion

    return mock_openai_client


def test_search_news(mocker):
    mock_ai_service = mocker.MagicMock(spec=AIService)
    mock_ai_service.extract_keywords.return_value = "keywords"
    mock_ai_service.summarize_news.return_value = {
        "影響": "test impact",
        "原因": "test reason",
    }

    # Mock the crawler's get_headline method to return test headlines
    from src.crawler.crawler_base import Headline, News

    test_headline = Headline(title="Test Headline", url="https://example.com/news1")

    test_news = News(
        title="Test Title", url="https://example.com/news1", time="2024-09-10", content="This is a test paragraph."
    )

    # Mock the service's crawler methods
    def get_mock_news_service(db=Depends(get_db)):
        mock_crawler = mocker.MagicMock()
        mock_crawler.get_headline.return_value = [test_headline]
        mock_crawler.parse.return_value = test_news
        news_service = NewsService(db, mock_crawler, mock_ai_service)
        return news_service

    app.dependency_overrides[get_news_service] = get_mock_news_service

    request_body = {"prompt": "Test search prompt"}
    response = client.post("/api/v1/news/search_news", json=request_body)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Title"
    assert data[0]["time"] == "2024-09-10"
    assert data[0]["content"] == "This is a test paragraph."


def test_news_summary(mocker, test_token):
    headers = {"Authorization": f"Bearer {test_token}"}

    mock_ai_service = mocker.MagicMock(spec=AIService)
    mock_ai_service.summarize_news.return_value = {
        "影響": "test impact",
        "原因": "test reason",
    }

    def get_mocked_news_service(db=Depends(get_db)):
        mock_crawler = mocker.MagicMock()
        return NewsService(db, mock_crawler, mock_ai_service)

    app.dependency_overrides[get_news_service] = get_mocked_news_service

    request_body = NewsSummaryRequest(content="Test news content")
    response = client.post("/api/v1/news/news_summary", json=request_body.dict(), headers=headers)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["summary"] == "test impact"
    assert json_response["reason"] == "test reason"


def test_upvote_article(test_user_and_articles, test_token):
    user, articles = test_user_and_articles
    headers = {"Authorization": f"Bearer {test_token}"}

    response = client.post(f"/api/v1/news/{articles[0].id}/upvote", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Article upvoted"


def test_downvote_article(test_user_and_articles, test_token):
    user, articles = test_user_and_articles
    headers = {"Authorization": f"Bearer {test_token}"}

    response = client.post(f"/api/v1/news/{articles[0].id}/upvote", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Upvote removed"
