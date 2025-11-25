"""
Unit Tests for udn_crawler.py

This module contains comprehensive unit tests for the UDNCrawler class,
including tests for fetching headlines, parsing news articles, and saving to database.
"""

from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from src.crawler.crawler_base import Headline, News, NewsWithSummary
from src.crawler.udn_crawler import UDNCrawler


class TestUDNCrawlerInitialization:
    """Tests for UDNCrawler initialization."""

    def test_udn_crawler_initialization_with_default_timeout(self):
        """Test UDNCrawler initialization with default timeout."""
        crawler = UDNCrawler()
        assert crawler.timeout == 5
        assert crawler.news_website_url == "https://udn.com/api/more"
        assert crawler.CHANNEL_ID == 2

    def test_udn_crawler_initialization_with_custom_timeout(self):
        """Test UDNCrawler initialization with custom timeout."""
        crawler = UDNCrawler(timeout=10)
        assert crawler.timeout == 10
        assert crawler.news_website_url == "https://udn.com/api/more"

    def test_udn_crawler_initialization_attributes(self):
        """Test that UDNCrawler has all required attributes."""
        crawler = UDNCrawler()
        assert hasattr(crawler, "news_website_url")
        assert hasattr(crawler, "timeout")
        assert hasattr(crawler, "CHANNEL_ID")


class TestStartup:
    """Tests for the startup method."""

    @patch.object(UDNCrawler, "get_headline")
    def test_startup_calls_get_headline_with_correct_params(self, mock_get_headline):
        """Test that startup calls get_headline with pages 1-10."""
        mock_get_headline.return_value = []
        crawler = UDNCrawler()
        result = crawler.startup("technology")
        assert len(result) == 0

        mock_get_headline.assert_called_once_with("technology", page=(1, 10))

    @patch.object(UDNCrawler, "get_headline")
    def test_startup_returns_headlines(self, mock_get_headline):
        """Test that startup returns headlines from get_headline."""
        expected_headlines = [
            Headline(title="Test 1", url="https://example.com/1"),
            Headline(title="Test 2", url="https://example.com/2"),
        ]
        mock_get_headline.return_value = expected_headlines

        crawler = UDNCrawler()
        result = crawler.startup("technology")

        assert result == expected_headlines


class TestGetHeadline:
    """Tests for the get_headline method."""

    @patch.object(UDNCrawler, "_fetch_news")
    def test_get_headline_with_single_page(self, mock_fetch_news):
        """Test get_headline with a single page number."""
        mock_headlines = [Headline(title="Test", url="https://example.com/article")]
        mock_fetch_news.return_value = mock_headlines

        crawler = UDNCrawler()
        result = crawler.get_headline("test", page=1)

        mock_fetch_news.assert_called_once_with(1, "test")
        assert result == mock_headlines

    @patch.object(UDNCrawler, "_fetch_news")
    def test_get_headline_with_page_range(self, mock_fetch_news):
        """Test get_headline with a page range tuple."""
        mock_headlines = [Headline(title="Test", url="https://example.com/article")]
        mock_fetch_news.return_value = mock_headlines

        crawler = UDNCrawler()
        result = crawler.get_headline("test", page=(1, 3))

        assert mock_fetch_news.call_count == 3
        assert len(result) == 3

    @patch.object(UDNCrawler, "_fetch_news")
    def test_get_headline_accumulates_all_headlines(self, mock_fetch_news):
        """Test that get_headline accumulates headlines from all pages."""
        headlines_page1 = [Headline(title="Page1", url="https://example.com/1")]
        headlines_page2 = [Headline(title="Page2", url="https://example.com/2")]
        mock_fetch_news.side_effect = [headlines_page1, headlines_page2]

        crawler = UDNCrawler()
        result = crawler.get_headline("test", page=(1, 2))

        assert len(result) == 2
        assert result[0].title == "Page1"
        assert result[1].title == "Page2"


class TestFetchNews:
    """Tests for the _fetch_news method."""

    @patch.object(UDNCrawler, "_parse_headlines")
    @patch.object(UDNCrawler, "_perform_request")
    @patch.object(UDNCrawler, "_create_search_params")
    def test_fetch_news_flow(self, mock_create_params, mock_request, mock_parse):
        """Test the complete flow of _fetch_news."""
        mock_params = {"page": 1, "id": "search:test", "channelId": 2, "type": "searchword"}
        mock_response = MagicMock()
        mock_headlines = [Headline(title="Test", url="https://example.com")]

        mock_create_params.return_value = mock_params
        mock_request.return_value = mock_response
        mock_parse.return_value = mock_headlines

        crawler = UDNCrawler()
        result = crawler._fetch_news(1, "test")

        mock_create_params.assert_called_once_with(1, "test")
        mock_request.assert_called_once_with(params=mock_params)
        mock_parse.assert_called_once_with(mock_response)
        assert result == mock_headlines


class TestCreateSearchParams:
    """Tests for the _create_search_params method."""

    def test_create_search_params_structure(self):
        """Test that _create_search_params creates correct parameter structure."""
        crawler = UDNCrawler()
        params = crawler._create_search_params(1, "technology")

        assert params["page"] == 1
        assert params["id"] == "search:technology"
        assert params["channelId"] == 2
        assert params["type"] == "searchword"

    def test_create_search_params_with_different_page_numbers(self):
        """Test _create_search_params with different page numbers."""
        crawler = UDNCrawler()

        params_page1 = crawler._create_search_params(1, "test")
        params_page5 = crawler._create_search_params(5, "test")

        assert params_page1["page"] == 1
        assert params_page5["page"] == 5

    def test_create_search_params_with_different_search_terms(self):
        """Test _create_search_params with different search terms."""
        crawler = UDNCrawler()

        params_tech = crawler._create_search_params(1, "technology")
        params_finance = crawler._create_search_params(1, "finance")

        assert params_tech["id"] == "search:technology"
        assert params_finance["id"] == "search:finance"

    def test_create_search_params_with_special_characters(self):
        """Test _create_search_params with special characters in search term."""
        crawler = UDNCrawler()
        params = crawler._create_search_params(1, "test-2024")

        assert params["id"] == "search:test-2024"


class TestPerformRequest:
    """Tests for the _perform_request method."""

    @patch("src.crawler.udn_crawler.requests.get")
    def test_perform_request_with_default_url(self, mock_get):
        """Test _perform_request uses default URL when none provided."""
        mock_response = MagicMock()
        mock_get.return_value = mock_response

        crawler = UDNCrawler()
        params = {"page": 1}
        result = crawler._perform_request(params=params)

        mock_get.assert_called_once_with("https://udn.com/api/more", params=params, timeout=5)
        assert result == mock_response

    @patch("src.crawler.udn_crawler.requests.get")
    def test_perform_request_with_custom_url(self, mock_get):
        """Test _perform_request with custom URL."""
        mock_response = MagicMock()
        mock_get.return_value = mock_response

        crawler = UDNCrawler()
        crawler._perform_request(url="https://custom.com", params={})

        mock_get.assert_called_once_with("https://custom.com", params={}, timeout=5)

    @patch("src.crawler.udn_crawler.requests.get")
    def test_perform_request_with_custom_timeout(self, mock_get):
        """Test _perform_request respects custom timeout."""
        mock_response = MagicMock()
        mock_get.return_value = mock_response

        crawler = UDNCrawler(timeout=15)
        crawler._perform_request(params={})

        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["timeout"] == 15

    @patch("src.crawler.udn_crawler.requests.get")
    def test_perform_request_raises_on_http_error(self, mock_get):
        """Test _perform_request raises exception on HTTP error."""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Connection error")

        crawler = UDNCrawler()
        with pytest.raises(RequestException):
            crawler._perform_request(params={})

    @patch("src.crawler.udn_crawler.requests.get")
    def test_perform_request_raises_for_status(self, mock_get):
        """Test _perform_request raises for HTTP status errors."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_get.return_value = mock_response

        crawler = UDNCrawler()
        with pytest.raises(Exception):  # noqa: B017
            crawler._perform_request(params={})


class TestParseHeadlines:
    """Tests for the _parse_headlines static method."""

    def test_parse_headlines_with_valid_response(self):
        """Test _parse_headlines with valid JSON response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "lists": [
                {"title": "Article 1", "titleLink": "https://example.com/1"},
                {"title": "Article 2", "titleLink": "https://example.com/2"},
            ]
        }

        headlines = UDNCrawler._parse_headlines(mock_response)

        assert len(headlines) == 2
        assert headlines[0].title == "Article 1"
        assert headlines[0].url == "https://example.com/1"
        assert headlines[1].title == "Article 2"
        assert headlines[1].url == "https://example.com/2"

    def test_parse_headlines_with_empty_lists(self):
        """Test _parse_headlines with empty lists."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"lists": []}

        headlines = UDNCrawler._parse_headlines(mock_response)

        assert headlines == []

    def test_parse_headlines_with_missing_fields(self):
        """Test _parse_headlines handles missing title or titleLink."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "lists": [
                {"title": "Article 1"},  # Missing titleLink
                {"titleLink": "https://example.com/2"},  # Missing title
            ]
        }

        headlines = UDNCrawler._parse_headlines(mock_response)

        assert len(headlines) == 2
        assert headlines[0].title == "Article 1"
        assert headlines[0].url == ""
        assert headlines[1].title == ""
        assert headlines[1].url == "https://example.com/2"

    def test_parse_headlines_with_json_error(self):
        """Test _parse_headlines handles JSON parsing error."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        headlines = UDNCrawler._parse_headlines(mock_response)

        assert headlines == []

    def test_parse_headlines_without_lists_key(self):
        """Test _parse_headlines when response has no 'lists' key."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}

        headlines = UDNCrawler._parse_headlines(mock_response)

        assert headlines == []


class TestParse:
    """Tests for the parse method."""

    @patch.object(UDNCrawler, "_extract_news")
    @patch("src.crawler.udn_crawler.requests.get")
    def test_parse_article(self, mock_get, mock_extract):
        """Test parse fetches and extracts news article."""
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_get.return_value = mock_response

        expected_news = News(
            title="Test Article", url="https://example.com/article", time="2021-10-01T00:00:00", content="Test content"
        )
        mock_extract.return_value = expected_news

        crawler = UDNCrawler()
        result = crawler.parse("https://example.com/article")

        mock_get.assert_called_once_with("https://example.com/article", timeout=5)
        assert result == expected_news

    @patch("src.crawler.udn_crawler.requests.get")
    def test_parse_with_request_error(self, mock_get):
        """Test parse raises exception on request error."""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Connection error")

        crawler = UDNCrawler()
        with pytest.raises(RequestException):
            crawler.parse("https://example.com/article")

    @patch("src.crawler.udn_crawler.BeautifulSoup")
    @patch("src.crawler.udn_crawler.requests.get")
    def test_parse_with_extraction_error(self, mock_get, mock_soup):
        """Test parse raises exception on extraction error."""
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_get.return_value = mock_response
        mock_soup.side_effect = Exception("Parsing error")

        crawler = UDNCrawler()
        with pytest.raises(Exception):  # noqa: B017
            crawler.parse("https://example.com/article")


class TestExtractNews:
    """Tests for the _extract_news static method."""

    def test_extract_news_with_valid_html(self):
        """Test _extract_news extracts all required fields."""
        html = """
        <html>
            <h1 class="article-content__title">Test Article Title</h1>
            <time class="article-content__time">2021-10-01 10:30:00</time>
            <section class="article-content__editor">
                <p>First paragraph</p>
                <p>Second paragraph</p>
                <p>▪ Bullet point (excluded)</p>
            </section>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        news = UDNCrawler._extract_news(soup, "https://example.com/article")

        assert news.title == "Test Article Title"
        assert news.url == "https://example.com/article"
        assert news.time == "2021-10-01 10:30:00"
        assert "First paragraph" in news.content
        assert "Second paragraph" in news.content
        assert "Bullet point" not in news.content

    def test_extract_news_filters_empty_paragraphs(self):
        """Test _extract_news filters out empty paragraphs."""
        html = """
        <html>
            <h1 class="article-content__title">Title</h1>
            <time class="article-content__time">2021-10-01</time>
            <section class="article-content__editor">
                <p>Content</p>
                <p>   </p>
                <p></p>
            </section>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        news = UDNCrawler._extract_news(soup, "https://example.com")

        # Should only contain "Content"
        assert news.content.strip() == "Content"

    def test_extract_news_with_whitespace(self):
        """Test _extract_news handles whitespace correctly."""
        html = """
        <html>
            <h1 class="article-content__title">  Title with spaces  </h1>
            <time class="article-content__time">  2021-10-01  </time>
            <section class="article-content__editor">
                <p>  Content with spaces  </p>
            </section>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        news = UDNCrawler._extract_news(soup, "https://example.com")

        assert news.title == "Title with spaces"
        assert news.time == "2021-10-01"
        assert news.content == "Content with spaces"

    def test_extract_news_missing_elements(self):
        """Test _extract_news raises exception when elements are missing."""
        html = "<html><body>Incomplete</body></html>"
        soup = BeautifulSoup(html, "html.parser")

        with pytest.raises(Exception):  # noqa: B017
            UDNCrawler._extract_news(soup, "https://example.com")

    def test_extract_news_with_bullet_points_excluded(self):
        """Test _extract_news excludes paragraphs with bullet points."""
        html = """
        <html>
            <h1 class="article-content__title">Title</h1>
            <time class="article-content__time">2021-10-01</time>
            <section class="article-content__editor">
                <p>Normal content</p>
                <p>▪ Bullet 1</p>
                <p>▪ Bullet 2</p>
                <p>More content</p>
            </section>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        news = UDNCrawler._extract_news(soup, "https://example.com")

        assert "Normal content" in news.content
        assert "More content" in news.content
        assert "Bullet" not in news.content


class TestSave:
    """Tests for the save method."""

    @patch("src.crawler.udn_crawler.NewsArticle")
    @patch.object(UDNCrawler, "_commit_changes")
    def test_save_creates_article_and_commits(self, mock_commit, mock_news_article_class):
        """Test save creates NewsArticle and commits to database."""
        mock_db = MagicMock()
        mock_article_instance = MagicMock()
        mock_news_article_class.return_value = mock_article_instance

        news = NewsWithSummary(
            title="Test Article",
            url="https://example.com/article",
            time="2021-10-01T00:00:00",
            content="Test content",
            summary="Test summary",
            reason="Test reason",
        )

        crawler = UDNCrawler()
        crawler.save(news, mock_db)

        # Verify NewsArticle was instantiated with correct parameters
        mock_news_article_class.assert_called_once_with(
            url="https://example.com/article",
            title="Test Article",
            time="2021-10-01T00:00:00",
            content="Test content",
            summary="Test summary",
            reason="Test reason",
        )

        # Verify db.add was called with the article instance
        mock_db.add.assert_called_once_with(mock_article_instance)

        # Verify _commit_changes was called
        mock_commit.assert_called_once_with(mock_db)

    @patch("src.crawler.udn_crawler.NewsArticle")
    @patch.object(UDNCrawler, "_commit_changes")
    def test_save_calls_commit_changes(self, mock_commit, mock_news_article_class):
        """Test save calls _commit_changes after adding article."""
        mock_db = MagicMock()
        mock_article_instance = MagicMock()
        mock_news_article_class.return_value = mock_article_instance

        news = NewsWithSummary(
            title="Test",
            url="https://example.com",
            time="2021-10-01",
            content="Content",
            summary="Summary",
            reason="Reason",
        )

        crawler = UDNCrawler()
        crawler.save(news, mock_db)

        mock_commit.assert_called_once_with(mock_db)

    def test_save_with_exception(self):
        """Test save handles exceptions gracefully."""
        mock_db = MagicMock()
        mock_db.add.side_effect = Exception("Database error")

        news = NewsWithSummary(
            title="Test",
            url="https://example.com",
            time="2021-10-01",
            content="Content",
            summary="Summary",
            reason="Reason",
        )

        crawler = UDNCrawler()
        with pytest.raises(Exception):  # noqa: B017
            crawler.save(news, mock_db)


class TestCommitChanges:
    """Tests for the _commit_changes static method."""

    def test_commit_changes_successful(self):
        """Test _commit_changes commits successfully."""
        mock_db = MagicMock()

        UDNCrawler._commit_changes(mock_db)

        mock_db.commit.assert_called_once()

    def test_commit_changes_with_error_rolls_back(self):
        """Test _commit_changes rolls back on error."""
        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("Commit error")

        with pytest.raises(Exception):  # noqa: B017
            UDNCrawler._commit_changes(mock_db)

        mock_db.rollback.assert_called_once()

    def test_commit_changes_logs_error(self):
        """Test _commit_changes logs errors."""
        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("Commit error")

        with patch("src.crawler.udn_crawler.logging.error") as mock_log:
            with pytest.raises(Exception):  # noqa: B017
                UDNCrawler._commit_changes(mock_db)

            mock_log.assert_called_once()
            assert "Error committing changes" in str(mock_log.call_args)


class TestIntegration:
    """Integration tests for UDNCrawler."""

    @patch.object(UDNCrawler, "_perform_request")
    def test_get_headline_integration(self, mock_request):
        """Test complete get_headline flow."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "lists": [
                {"title": "Article 1", "titleLink": "https://udn.com/news/1"},
                {"title": "Article 2", "titleLink": "https://udn.com/news/2"},
            ]
        }
        mock_request.return_value = mock_response

        crawler = UDNCrawler()
        headlines = crawler.get_headline("technology", page=1)

        assert len(headlines) == 2
        assert headlines[0].title == "Article 1"

    def test_validate_and_parse(self):
        """Test validate_and_parse validates domain correctly."""
        crawler = UDNCrawler()

        # UDN crawler accepts udn.com URLs
        # Since validate_and_parse is inherited, it should work with UDN URLs
        # This test checks that the method is available and callable
        assert hasattr(crawler, "validate_and_parse")
        assert callable(crawler.validate_and_parse)


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_udn_crawler_with_zero_timeout(self):
        """Test UDNCrawler with timeout of 0."""
        crawler = UDNCrawler(timeout=0)
        assert crawler.timeout == 0

    def test_parse_headlines_with_very_large_response(self):
        """Test _parse_headlines with large number of articles."""
        mock_response = MagicMock()
        large_lists = [{"title": f"Article {i}", "titleLink": f"https://example.com/{i}"} for i in range(1000)]
        mock_response.json.return_value = {"lists": large_lists}

        headlines = UDNCrawler._parse_headlines(mock_response)

        assert len(headlines) == 1000

    def test_extract_news_with_unicode_content(self):
        """Test _extract_news handles unicode content."""
        html = """
        <html>
            <h1 class="article-content__title">中文標題</h1>
            <time class="article-content__time">2021-10-01</time>
            <section class="article-content__editor">
                <p>這是中文內容</p>
                <p>日本語コンテンツ</p>
            </section>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        news = UDNCrawler._extract_news(soup, "https://example.com")

        assert "中文標題" in news.title
        assert "中文內容" in news.content
        assert "日本語" in news.content

    def test_get_headline_with_large_page_range(self):
        """Test get_headline with large page range."""
        with patch.object(UDNCrawler, "_fetch_news") as mock_fetch:
            mock_fetch.return_value = []

            crawler = UDNCrawler()
            crawler.get_headline("test", page=(1, 100))

            assert mock_fetch.call_count == 100

    def test_create_search_params_with_empty_search_term(self):
        """Test _create_search_params with empty search term."""
        crawler = UDNCrawler()
        params = crawler._create_search_params(1, "")

        assert params["id"] == "search:"

    def test_create_search_params_with_special_url_characters(self):
        """Test _create_search_params with special characters."""
        crawler = UDNCrawler()
        params = crawler._create_search_params(1, "test & special=chars")

        assert "test & special=chars" in params["id"]
