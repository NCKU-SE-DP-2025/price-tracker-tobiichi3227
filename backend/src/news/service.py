import itertools
import json
import logging

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from sqlalchemy.orm import Session

from src.news.config import news_settings
from src.news.models import NewsArticle, user_news_association_table


class AIService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def evaluate_relevance(self, title: str) -> str:
        return self._call_ai(news_settings.AI_RELEVANCE_PROMPT, title)

    def summarize_news(self, content: str) -> dict:
        result = self._call_ai(news_settings.AI_SUMMARY_PROMPT, content)
        return json.loads(result)

    def extract_keywords(self, prompt: str) -> str:
        return self._call_ai(news_settings.AI_KEYWORD_PROMPT, prompt)

    def _call_ai(self, system: str, user_content: str) -> str:
        completion = self.client.chat.completions.create(
            model=news_settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        return completion.choices[0].message.content


ai_service = AIService(api_key=news_settings.OPENAI_API_KEY)


class NewsService:
    _id_counter = itertools.count(start=1000000)

    def __init__(self, db: Session, ai_service: AIService = ai_service):
        self.db = db
        self.ai_service = ai_service

    def add_news_article(self, news_data: dict) -> NewsArticle:
        article = NewsArticle(
            url=news_data["url"],
            title=news_data["title"],
            time=news_data["time"],
            content=news_data["content"],
            summary=news_data["summary"],
            reason=news_data["reason"],
        )
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)
        return article

    def get_all_articles(self) -> list[NewsArticle]:
        return self.db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()

    def count_upvote(self, article_id: int) -> int:
        return (
            self.db.query(user_news_association_table)
            .filter_by(news_articles_id=article_id)
            .count()
        )

    def is_upvoted_by_user(self, article_id: int, user_id: int) -> bool:
        return (
            self.db.query(user_news_association_table)
            .filter_by(news_articles_id=article_id, user_id=user_id)
            .first()
            is not None
        )

    def toggle_upvote(self, article_id: int, user_id: int) -> bool:
        if self.is_upvoted_by_user(article_id, user_id):
            from sqlalchemy import delete

            delete_stmt = delete(user_news_association_table).where(
                user_news_association_table.c.news_articles_id == article_id,
                user_news_association_table.c.user_id == user_id,
            )
            self.db.execute(delete_stmt)
            self.db.commit()
            return False
        else:
            from sqlalchemy import insert

            insert_stmt = insert(user_news_association_table).values(
                news_articles_id=article_id, user_id=user_id
            )
            self.db.execute(insert_stmt)
            self.db.commit()
            return True

    def fetch_and_process_news(
        self, search_term: str, is_initial: bool = False
    ) -> None:
        raw_news = self._fetch_raw_news(search_term, is_initial)
        for news in raw_news:
            try:
                self._process_single_news(news)
            except Exception as e:
                logging.error(f"Error processing news {news.get('titleLink')}: {e}")

    def _process_single_news(self, raw_news: dict):
        relevance = self.ai_service.evaluate_relevance(raw_news["title"])
        if relevance != "high":
            return
        detailed = self._fetch_detailed_news(raw_news["titleLink"])
        if not detailed:
            return
        summary_data = self.ai_service.summarize_news(detailed["content"])
        detailed["summary"] = summary_data["影響"]
        detailed["reason"] = summary_data["原因"]
        self.add_news_article(detailed)

    def _fetch_raw_news(self, search_term: str, is_initial: bool = False) -> list[dict]:
        all_news = []
        pages = range(1, 10) if is_initial else range(1, 2)
        for page in pages:
            params = {
                "page": page,
                "id": f"search:{search_term}",
                "channelId": 2,
                "type": "searchword",
            }
            try:
                response = requests.get(
                    news_settings.UDN_API_URL, params=params, timeout=10
                )
                all_news.extend(response.json().get("lists", []))
            except Exception as e:
                logging.error(f"Error fetching raw news for page {page}: {e}")
        return all_news

    def _fetch_detailed_news(self, url: str) -> dict | None:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find("h1", class_="article-content__title").text
            time = soup.find("time", class_="article-content__time").text
            content_section = soup.find("section", class_="article-content__editor")
            paragraphs = [
                p.text
                for p in content_section.find_all("p")
                if p.text.strip() != "" and "▪" not in p.text
            ]
            return {
                "url": url,
                "title": title,
                "time": time,
                "content": "".join(paragraphs),
                "id": next(self._id_counter),
            }
        except Exception as e:
            logging.error(f"Error fetching detailed from {url} news: {e}")
            return None

    def search_by_prompt(self, prompt: str) -> list:
        keyword = self.ai_service.extract_keywords(prompt)
        news_list = self._fetch_raw_news(keyword, is_initial=False)
        results = []
        for news in news_list:
            detailed = self._fetch_detailed_news(news["titleLink"])
            if not detailed:
                continue
            results.append(detailed)
        return sorted(results, key=lambda x: x["time"], reverse=True)
