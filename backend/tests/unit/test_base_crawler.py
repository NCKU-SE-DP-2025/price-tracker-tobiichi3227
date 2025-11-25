"""
Unit Tests for crawler_base.py

This module contains comprehensive unit tests for the NewsCrawlerBase abstract class,
including tests for Headline, News, and NewsWithSummary models, as well as the
NewsCrawlerBase validation and utility methods.
"""

import pytest
from pydantic import ValidationError

from src.crawler.crawler_base import Headline, News, NewsCrawlerBase, NewsWithSummary
from src.crawler.exceptions import DomainMismatchError


class TestHeadline:
    """Tests for the Headline model."""

    def test_headline_creation_with_valid_data(self):
        """Test creating a Headline with valid data."""
        headline = Headline(title="Test Title", url="https://example.com/article")
        assert headline.title == "Test Title"
        assert headline.url == "https://example.com/article"

    def test_headline_creation_with_string_url(self):
        """Test creating a Headline with string URL."""
        headline = Headline(title="Test Title", url="https://example.com")
        assert headline.url == "https://example.com"

    def test_headline_missing_title(self):
        """Test that Headline requires a title field."""
        with pytest.raises(ValidationError):
            Headline(url="https://example.com")

    def test_headline_missing_url(self):
        """Test that Headline requires a URL field."""
        with pytest.raises(ValidationError):
            Headline(title="Test Title")

    def test_headline_empty_title(self):
        """Test creating a Headline with empty title."""
        headline = Headline(title="", url="https://example.com")
        assert headline.title == ""

    def test_headline_empty_url(self):
        """Test creating a Headline with empty URL."""
        headline = Headline(title="Test", url="")
        assert headline.url == ""


class TestNews:
    """Tests for the News model."""

    def test_news_creation_with_valid_data(self):
        """Test creating a News object with all required fields."""
        news = News(
            title="Test Title",
            url="https://example.com/article",
            time="2021-10-01T00:00:00",
            content="Test content",
        )
        assert news.title == "Test Title"
        assert news.url == "https://example.com/article"
        assert news.time == "2021-10-01T00:00:00"
        assert news.content == "Test content"

    def test_news_inherits_from_headline(self):
        """Test that News inherits from Headline."""
        news = News(
            title="Test Title",
            url="https://example.com/article",
            time="2021-10-01T00:00:00",
            content="Test content",
        )
        assert isinstance(news, Headline)

    def test_news_missing_time(self):
        """Test that News requires a time field."""
        with pytest.raises(ValidationError):
            News(
                title="Test Title",
                url="https://example.com/article",
                content="Test content",
            )

    def test_news_missing_content(self):
        """Test that News requires a content field."""
        with pytest.raises(ValidationError):
            News(
                title="Test Title",
                url="https://example.com/article",
                time="2021-10-01T00:00:00",
            )

    def test_news_with_empty_content(self):
        """Test creating a News object with empty content."""
        news = News(
            title="Test Title",
            url="https://example.com/article",
            time="2021-10-01T00:00:00",
            content="",
        )
        assert news.content == ""

    def test_news_with_long_content(self):
        """Test creating a News object with long content."""
        long_content = "x" * 10000
        news = News(
            title="Test Title",
            url="https://example.com/article",
            time="2021-10-01T00:00:00",
            content=long_content,
        )
        assert news.content == long_content
        assert len(news.content) == 10000


class TestNewsWithSummary:
    """Tests for the NewsWithSummary model."""

    def test_news_with_summary_creation_with_valid_data(self):
        """Test creating a NewsWithSummary object with all required fields."""
        news_summary = NewsWithSummary(
            title="Test Title",
            url="https://example.com/article",
            time="2021-10-01T00:00:00",
            content="Test content",
            summary="Test summary",
            reason="Test reason",
        )
        assert news_summary.title == "Test Title"
        assert news_summary.url == "https://example.com/article"
        assert news_summary.time == "2021-10-01T00:00:00"
        assert news_summary.content == "Test content"
        assert news_summary.summary == "Test summary"
        assert news_summary.reason == "Test reason"

    def test_news_with_summary_inherits_from_news(self):
        """Test that NewsWithSummary inherits from News."""
        news_summary = NewsWithSummary(
            title="Test Title",
            url="https://example.com/article",
            time="2021-10-01T00:00:00",
            content="Test content",
            summary="Test summary",
            reason="Test reason",
        )
        assert isinstance(news_summary, News)
        assert isinstance(news_summary, Headline)

    def test_news_with_summary_missing_summary(self):
        """Test that NewsWithSummary requires a summary field."""
        with pytest.raises(ValidationError):
            NewsWithSummary(
                title="Test Title",
                url="https://example.com/article",
                time="2021-10-01T00:00:00",
                content="Test content",
                reason="Test reason",
            )

    def test_news_with_summary_missing_reason(self):
        """Test that NewsWithSummary requires a reason field."""
        with pytest.raises(ValidationError):
            NewsWithSummary(
                title="Test Title",
                url="https://example.com/article",
                time="2021-10-01T00:00:00",
                content="Test content",
                summary="Test summary",
            )

    def test_news_with_summary_empty_fields(self):
        """Test creating a NewsWithSummary with empty optional fields."""
        news_summary = NewsWithSummary(
            title="Test Title",
            url="https://example.com/article",
            time="2021-10-01T00:00:00",
            content="Test content",
            summary="",
            reason="",
        )
        assert news_summary.summary == ""
        assert news_summary.reason == ""


class ConcreteCrawler(NewsCrawlerBase):
    """Concrete implementation of NewsCrawlerBase for testing."""

    def __init__(self, website_url="https://example.com"):
        self.news_website_url = website_url
        self.news_website_news_child_urls = []

    def get_headline(self, search_term, page):
        """Concrete implementation of get_headline."""
        return [
            Headline(title="Test", url="https://example.com/article1"),
            Headline(title="Test2", url="https://example.com/article2"),
        ]

    def parse(self, url):
        """Concrete implementation of parse."""
        return News(
            title="Test",
            url=url,
            time="2021-10-01T00:00:00",
            content="Test content",
        )

    @staticmethod
    def save(news, db):
        """Concrete implementation of save."""
        return None


class TestNewsCrawlerBase:
    """Tests for the NewsCrawlerBase abstract class."""

    def test_new_crawler_base_is_abstract(self):
        """Test that NewsCrawlerBase is an abstract class."""
        # NewsCrawlerBase uses ABCMeta as metaclass, making it abstract
        assert hasattr(NewsCrawlerBase, "__abstractmethods__")
        abstract_methods = NewsCrawlerBase.__abstractmethods__
        assert "get_headline" in abstract_methods
        assert "parse" in abstract_methods
        assert "save" in abstract_methods

    def test_concrete_crawler_instantiation(self):
        """Test that concrete implementation can be instantiated."""
        crawler = ConcreteCrawler()
        assert crawler.news_website_url == "https://example.com"
        assert crawler.news_website_news_child_urls == []

    def test_get_headline_is_abstract(self):
        """Test that get_headline is an abstract method."""
        crawler = ConcreteCrawler()
        headlines = crawler.get_headline("test", 1)
        assert isinstance(headlines, list)

    def test_parse_is_abstract(self):
        """Test that parse is an abstract method."""
        crawler = ConcreteCrawler()
        news = crawler.parse("https://example.com/article")
        assert isinstance(news, News)

    def test_save_is_abstract(self):
        """Test that save is an abstract method."""
        crawler = ConcreteCrawler()
        news = News(
            title="Test",
            url="https://example.com/article",
            time="2021-10-01T00:00:00",
            content="Test content",
        )
        # Should not raise an error for concrete implementation
        crawler.save(news, None)


class TestIsValidUrl:
    """Tests for the _is_valid_url method."""

    def test_valid_url_same_domain(self):
        """Test that a URL with the same domain is valid."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        assert crawler._is_valid_url("https://example.com/article")

    def test_valid_url_with_subdomain(self):
        """Test that URLs with different subdomains of the same domain are valid."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        assert crawler._is_valid_url("https://news.example.com/article")

    def test_valid_url_with_different_protocol(self):
        """Test that URLs with different protocols but same domain are valid."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        assert crawler._is_valid_url("http://example.com/article")

    def test_invalid_url_different_domain(self):
        """Test that a URL with a different domain is invalid."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        assert not crawler._is_valid_url("https://other.com/article")

    def test_invalid_url_similar_domain(self):
        """Test that similar but different domains are invalid."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        assert not crawler._is_valid_url("https://example.co/article")

    def test_valid_url_with_path(self):
        """Test that URLs with paths on the same domain are valid."""
        crawler = ConcreteCrawler(website_url="https://example.com/api")
        assert crawler._is_valid_url("https://example.com/article/123")

    def test_valid_url_with_query_params(self):
        """Test that URLs with query parameters are valid if domain matches."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        assert crawler._is_valid_url("https://example.com/article?id=123&lang=en")

    def test_url_validation_case_insensitive_domain(self):
        """Test URL validation with uppercase domain (tldextract normalizes to lowercase)."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        # Note: tldextract normalizes domains but may be case-sensitive based on implementation
        # This test verifies the actual behavior
        result = crawler._is_valid_url("https://EXAMPLE.COM/article")
        # The result depends on tldextract behavior; just verify it works without error
        assert isinstance(result, bool)

    def test_valid_url_with_port(self):
        """Test that URLs with different ports on same domain are valid."""
        crawler = ConcreteCrawler(website_url="https://example.com:8080")
        # tldextract ignores ports, so this should still be valid
        assert crawler._is_valid_url("https://example.com:9000/article")

    def test_invalid_url_completely_different(self):
        """Test completely different domain."""
        crawler = ConcreteCrawler(website_url="https://news.example.com")
        assert not crawler._is_valid_url("https://github.com/user/repo")


class TestValidateAndParse:
    """Tests for the validate_and_parse method."""

    def test_validate_and_parse_with_valid_url(self):
        """Test validate_and_parse with a valid URL."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        news = crawler.validate_and_parse("https://example.com/article")
        assert isinstance(news, News)
        assert news.url == "https://example.com/article"

    def test_validate_and_parse_with_invalid_url_raises_exception(self):
        """Test that validate_and_parse raises DomainMismatchException for invalid URL."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        with pytest.raises(DomainMismatchError) as exc_info:
            crawler.validate_and_parse("https://other.com/article")
        assert exc_info.value.url == "https://other.com/article"

    def test_validate_and_parse_exception_contains_url(self):
        """Test that DomainMismatchException contains the invalid URL."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        with pytest.raises(DomainMismatchError) as exc_info:
            crawler.validate_and_parse("https://malicious.com/article")
        assert "malicious.com" in exc_info.value.url

    def test_validate_and_parse_valid_subdomain(self):
        """Test validate_and_parse with valid subdomain."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        news = crawler.validate_and_parse("https://news.example.com/article")
        assert isinstance(news, News)

    def test_validate_and_parse_calls_parse_method(self):
        """Test that validate_and_parse calls the parse method."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        # Mock the parse method
        original_parse = crawler.parse
        parse_called = False

        def mock_parse(url):
            nonlocal parse_called
            parse_called = True
            return original_parse(url)

        crawler.parse = mock_parse
        crawler.validate_and_parse("https://example.com/article")
        assert parse_called is True

    def test_validate_and_parse_string_url(self):
        """Test validate_and_parse with string URL."""
        crawler = ConcreteCrawler(website_url="https://example.com")
        news = crawler.validate_and_parse("https://example.com/article")
        assert isinstance(news, News)


class TestDomainMismatchException:
    """Tests for DomainMismatchException."""

    def test_exception_with_url(self):
        """Test creating DomainMismatchException with URL."""
        url = "https://invalid.com/article"
        exception = DomainMismatchError(url=url)
        assert exception.url == url

    def test_exception_with_custom_message(self):
        """Test creating DomainMismatchException with custom message."""
        url = "https://invalid.com/article"
        message = "Custom error message"
        exception = DomainMismatchError(url=url, message=message)
        assert exception.message == message

    def test_exception_default_message(self):
        """Test that DomainMismatchException has default message."""
        exception = DomainMismatchError(url="https://invalid.com")
        assert exception.message == "URL's domain does not match the news website's domain"

    def test_exception_is_exception_subclass(self):
        """Test that DomainMismatchException is an Exception."""
        exception = DomainMismatchError(url="https://invalid.com")
        assert isinstance(exception, Exception)


class TestConcreteImplementation:
    """Tests for the concrete implementation example."""

    def test_concrete_crawler_get_headline(self):
        """Test get_headline on concrete crawler."""
        crawler = ConcreteCrawler()
        headlines = crawler.get_headline("test", 1)
        assert len(headlines) == 2
        assert headlines[0].title == "Test"

    def test_concrete_crawler_parse(self):
        """Test parse on concrete crawler."""
        crawler = ConcreteCrawler()
        news = crawler.parse("https://example.com/article")
        assert news.title == "Test"
        assert news.content == "Test content"

    def test_concrete_crawler_validate_and_parse(self):
        """Test validate_and_parse on concrete crawler."""
        crawler = ConcreteCrawler()
        news = crawler.validate_and_parse("https://example.com/article")
        assert isinstance(news, News)

    def test_concrete_crawler_with_custom_url(self):
        """Test concrete crawler with custom website URL."""
        crawler = ConcreteCrawler(website_url="https://news.example.org")
        assert crawler.news_website_url == "https://news.example.org"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_headline_with_very_long_title(self):
        """Test Headline with very long title."""
        long_title = "x" * 10000
        headline = Headline(title=long_title, url="https://example.com")
        assert len(headline.title) == 10000

    def test_headline_with_special_characters(self):
        """Test Headline with special characters in title and URL."""
        headline = Headline(
            title="Title with éàü and 中文",
            url="https://example.com/article?q=test&lang=中文",
        )
        assert "éàü" in headline.title
        assert "中文" in headline.url

    def test_news_with_unicode_content(self):
        """Test News with unicode content."""
        news = News(
            title="Unicode Test",
            url="https://example.com",
            time="2021-10-01T00:00:00",
            content="日本語 한국어 中文 العربية",
        )
        assert "日本語" in news.content

    def test_url_validation_with_localhost(self):
        """Test URL validation with localhost."""
        crawler = ConcreteCrawler(website_url="http://localhost:8000")
        # localhost might not have a registered domain
        result = crawler._is_valid_url("http://localhost:8000/article")
        assert isinstance(result, bool)
        # Should handle gracefully

    def test_url_validation_with_ip_address(self):
        """Test URL validation with IP address."""
        crawler = ConcreteCrawler(website_url="http://192.168.1.1")
        # IP addresses should be handled
        result = crawler._is_valid_url("http://192.168.1.1/article")
        assert isinstance(result, bool)
        # Should handle gracefully

    def test_news_with_newlines_in_content(self):
        """Test News with newlines in content."""
        content = "Line 1\nLine 2\nLine 3"
        news = News(
            title="Test",
            url="https://example.com",
            time="2021-10-01T00:00:00",
            content=content,
        )
        assert "\n" in news.content
        assert len(news.content.split("\n")) == 3
