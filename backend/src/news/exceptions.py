from http import HTTPStatus

from fastapi import HTTPException

from src.news.constants import (
    AI_SERVICE_ERROR,
    INVALID_NEWS_ID,
    NEWS_NOT_FOUND,
)


class NewsNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=HTTPStatus.NOT_FOUND, detail=NEWS_NOT_FOUND)


class InvalidNewsId(HTTPException):
    def __init__(self):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=INVALID_NEWS_ID)


class AIServiceError(HTTPException):
    def __init__(self):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=AI_SERVICE_ERROR)
