"""
UDN News Scraper Module

This module provides the UDNCrawler class for fetching, parsing, and saving news articles from the UDN website.
The class extends the NewsCrawlerBase and includes functionalities to search for news articles based on a search term,
parse the details of individual articles, and save them to a database using SQLAlchemy ORM.

Classes:
    UDNCrawler: A class to scrape news from UDN.

Exceptions:
    DomainMismatchException: Raised when the URL domain does not match the expected domain for the crawler.

Usage Example:
    crawler = UDNCrawler(timeout=10)
    headlines = crawler.startup("technology")
    for headline in headlines:
        news = crawler.parse(headline.url)
        crawler.save(news, db_session)

UDNCrawler Methods:
    __init__(self, timeout: int = 5): Initializes the crawler with a default timeout for HTTP requests.
    startup(self, search_term: str) -> list[Headline]: \
        Fetches news headlines for a given search term across multiple pages.
    get_headline(self, search_term: str, page: int | tuple[int, int]) -> list[Headline]: \
        Fetches news headlines for specified pages.
    _fetch_news(self, page: int, search_term: str) -> list[Headline]: \
        Helper method to fetch news headlines for a specific page.
    _create_search_params(self, page: int, search_term: str): Creates the parameters for the search request.
    _perform_request(self, params: dict): Performs the HTTP request to fetch news data.
    _parse_headlines(response): Parses the response to extract headlines.
    parse(self, url: str) -> News: Parses a news article from a given URL.
    _extract_news(soup, url: str) -> News: Extracts news details from the BeautifulSoup object.
    save(self, news: News, db: Session): Saves a news article to the database.
    _commit_changes(db: Session): Commits the changes to the database with error handling.
"""

import logging

import requests
from bs4 import BeautifulSoup
from requests import Response
from sqlalchemy.orm import Session

from src.news.models import NewsArticle

from .crawler_base import Headline, News, NewsCrawlerBase, NewsWithSummary


class UDNCrawler(NewsCrawlerBase):
    CHANNEL_ID = 2

    def __init__(self, timeout: int = 5) -> None:
        self.news_website_url = "https://udn.com/api/more"
        self.timeout = timeout

    def startup(self, search_term: str) -> list[Headline]:
        """
        Initializes the application by fetching news headlines for a given search term across multiple pages.
        This method is typically called at the beginning of the program when there is no data available,
        hence it fetches headlines from the first 10 pages.

        :param search_term: The term to search for in news headlines.
        :return: A list of Headline namedtuples containing the title and URL of news articles.
        :rtype: list[Headline]
        """
        return self.get_headline(search_term, page=(1, 10))

    def get_headline(self, search_term: str, page: int | tuple[int, int]) -> list[Headline]:
        """
        Fetches news headlines for a given search term and page(s).

        :param search_term: The search term to search for.
        :param page: A single page number (int) or a tuple of (start, end) page numbers (inclusive).
        :return: A list of Headline objects containing title and URL.
        """
        # Calculate the range of pages to fetch news from.
        page_range = range(page[0], page[1] + 1) if isinstance(page, tuple) else [page]

        all_headlines = []
        for p in page_range:
            headlines = self._fetch_news(p, search_term)
            all_headlines.extend(headlines)

        return all_headlines

    def _fetch_news(self, page: int, search_term: str) -> list[Headline]:
        """
        Helper method to fetch news headlines for a specific page.

        :param page: The page number to fetch.
        :param search_term: The search term to search for.
        :return: A list of Headline objects for the given page.
        """
        params = self._create_search_params(page, search_term)
        response = self._perform_request(params=params)
        return self._parse_headlines(response)

    def _create_search_params(self, page: int, search_term: str) -> dict:
        """
        Creates the parameters for the search request.

        :param page: The page number.
        :param search_term: The search term.
        :return: A dictionary containing the search parameters.
        """
        return {
            "page": page,
            "id": f"search:{search_term}",
            "channelId": self.CHANNEL_ID,
            "type": "searchword",
        }

    def _perform_request(self, url: str | None = None, params: dict | None = None) -> Response:
        """
        Performs the HTTP request to fetch news data.

        :param url: The URL to request from. If None, uses self.news_website_url.
        :param params: The parameters for the request.
        :return: The response object from the request.
        """
        request_url = url or self.news_website_url
        try:
            response = requests.get(request_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logging.error(f"Error performing request to {request_url}: {e}")
            raise

    @staticmethod
    def _parse_headlines(response: Response) -> list[Headline]:
        """
        Parses the response to extract headlines.

        :param response: The HTTP response object from the API.
        :return: A list of Headline objects extracted from the response.
        """
        try:
            data = response.json()
            headlines = []
            for item in data.get("lists", []):
                headline = Headline(
                    title=item.get("title", ""),
                    url=item.get("titleLink", ""),
                )
                headlines.append(headline)
            return headlines
        except Exception as e:
            logging.error(f"Error parsing headlines from response: {e}")
            return []

    def parse(self, url: str) -> News:
        """
        Parses a news article from a given URL.

        :param url: The URL of the news article.
        :return: A News object containing the article details.
        """
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            news = self._extract_news(soup, url)
            return news
        except Exception as e:
            logging.error(f"Error parsing news from {url}: {e}")
            raise

    @staticmethod
    def _extract_news(soup: BeautifulSoup, url: str) -> News:
        """
        Extracts news details from the BeautifulSoup object.

        :param soup: The BeautifulSoup object of the article page.
        :param url: The URL of the article.
        :return: A News object containing the extracted details.
        """
        try:
            title = soup.find("h1", class_="article-content__title").text.strip()
            time = soup.find("time", class_="article-content__time").text.strip()
            content_section = soup.find("section", class_="article-content__editor")
            paragraphs = [
                p.text.strip() for p in content_section.find_all("p") if p.text.strip() != "" and "▪" not in p.text
            ]
            content = "\n".join(paragraphs)

            return News(
                title=title,
                url=url,
                time=time,
                content=content,
            )
        except Exception as e:
            logging.error(f"Error extracting news from {url}: {e}")
            raise

    def save(self, news: NewsWithSummary, db: Session):
        """
        Saves a news article to the database.

        :param news: The NewsWithSummary object to save.
        :param db: The database session.
        """
        try:
            article = NewsArticle(
                url=str(news.url),
                title=news.title,
                time=news.time,
                content=news.content,
                summary=news.summary,
                reason=news.reason,
            )
            db.add(article)
            self._commit_changes(db)
        except Exception as e:
            logging.error(f"Error saving news article: {e}")
            raise

    @staticmethod
    def _commit_changes(db: Session):
        """
        Commits the changes to the database with error handling.

        :param db: The database session.
        """
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logging.error(f"Error committing changes to database: {e}")
            raise
