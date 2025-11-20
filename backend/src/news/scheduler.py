import logging

from apscheduler.schedulers.background import BackgroundScheduler

from src.database import SessionLocal
from src.news.config import news_settings
from src.news.models import NewsArticle
from src.news.service import NewsService, ai_service


class NewsScheduler:
    def __init__(self):
        self.schedulers = BackgroundScheduler()

    def start(self):
        db = SessionLocal()
        try:
            if db.query(NewsArticle).count() == 0:
                logging.info("Database empty, performing initial news fetch.")
                self._fetch_news(is_initial=True)

            self.schedulers.add_job(
                self._fetch_news,
                "interval",
                minutes=100,
                id="fetch_news",
            )
            self.schedulers.start()
            logging.info("News scheduler started.")
        finally:
            db.close()

    def shutdown(self):
        if self.schedulers.running:
            self.schedulers.shutdown()
            logging.info("News scheduler shut down.")

    def _fetch_news(self, is_initial=False):
        db = SessionLocal()
        try:
            news_service = NewsService(db, ai_service)
            news_service.fetch_and_process_news(
                news_settings.INITIAL_SEARCH_TERM, is_initial=is_initial
            )
            logging.info("Scheduled news fetch completed.")
        except Exception as e:
            logging.error(f"Error in scheduled news fetch: {e}")
        finally:
            db.close()
