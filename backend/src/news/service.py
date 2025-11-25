import json
import logging

from openai import OpenAI
from sqlalchemy.orm import Session

from src.crawler.crawler_base import NewsWithSummary
from src.crawler.udn_crawler import UDNCrawler
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
    def __init__(self, db: Session, crawler: "UDNCrawler", ai_service: AIService = ai_service):
        self.db = db
        self.crawler = crawler
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
        return self.db.query(user_news_association_table).filter_by(news_articles_id=article_id).count()

    def is_upvoted_by_user(self, article_id: int, user_id: int) -> bool:
        return (
            self.db.query(user_news_association_table).filter_by(news_articles_id=article_id, user_id=user_id).first()
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

            insert_stmt = insert(user_news_association_table).values(news_articles_id=article_id, user_id=user_id)
            self.db.execute(insert_stmt)
            self.db.commit()
            return True

    def fetch_and_process_news(self, search_term: str, is_initial: bool = False) -> None:
        """
        Fetches and processes news articles from UDN.

        :param search_term: The search term to search for.
        :param is_initial: If True, fetches from multiple pages (pages 1-10), otherwise just page 1.
        """
        try:
            # Fetch headlines based on whether it's initial or subsequent fetch
            if is_initial:
                headlines = self.crawler.startup(search_term)
            else:
                headlines = self.crawler.get_headline(search_term, page=1)

            # Process each headline
            for headline in headlines:
                try:
                    self._process_single_headline(headline)
                except Exception as e:
                    logging.error(f"Error processing headline {headline.title}: {e}")
        except Exception as e:
            logging.error(f"Error fetching and processing news for '{search_term}': {e}")

    def _process_single_headline(self, headline):
        """
        Processes a single headline: evaluates relevance, fetches details, and saves to database.

        :param headline: A Headline object containing title and URL.
        """
        # Evaluate relevance of the headline
        relevance = self.ai_service.evaluate_relevance(headline.title)
        if relevance != "high":
            logging.debug(f"Skipping '{headline.title}' due to low relevance")
            return

        # Parse and extract detailed news from the URL
        try:
            news = self.crawler.parse(str(headline.url))
        except Exception as e:
            logging.error(f"Error parsing news from {headline.url}: {e}")
            return

        # Summarize the news content
        try:
            summary_data = self.ai_service.summarize_news(news.content)
            summary = summary_data.get("影響", "")
            reason = summary_data.get("原因", "")
        except Exception as e:
            logging.error(f"Error summarizing news: {e}")
            return

        # Create NewsWithSummary object and save to database
        news_with_summary = NewsWithSummary(
            title=news.title,
            url=news.url,
            time=news.time,
            content=news.content,
            summary=summary,
            reason=reason,
        )

        try:
            self.crawler.save(news_with_summary, self.db)
            logging.info(f"Successfully saved article: {news.title}")
        except Exception as e:
            logging.error(f"Error saving article to database: {e}")

    def search_by_prompt(self, prompt: str) -> list:
        """
        Searches for news articles based on a user prompt.

        Uses AI to extract keywords from the prompt, fetches relevant news,
        and returns a sorted list of results.

        :param prompt: The user's search prompt.
        :return: A list of news articles sorted by time (most recent first).
        """
        try:
            # Extract keywords from the prompt
            keyword = self.ai_service.extract_keywords(prompt)
            logging.info(f"Extracted keyword from prompt: {keyword}")

            # Fetch headlines for the keyword
            headlines = self.crawler.get_headline(keyword, page=1)

            results = []
            for headline in headlines:
                try:
                    # Parse detailed news for each headline
                    news = self.crawler.parse(str(headline.url))
                    results.append(
                        {
                            "url": str(news.url),
                            "title": news.title,
                            "time": news.time,
                            "content": news.content,
                        }
                    )
                except Exception as e:
                    logging.error(f"Error parsing headline {headline.url}: {e}")
                    continue

            # Sort by time (most recent first)
            return sorted(results, key=lambda x: x["time"], reverse=True)
        except Exception as e:
            logging.error(f"Error searching by prompt: {e}")
            return []
