from http import HTTPStatus

from fastapi import HTTPException

from src.price.constants import (
    INVALID_PRICE_ID,
    PRICE_API_ERROR,
    PRICE_NOT_FOUND,
)


class PriceNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=HTTPStatus.NOT_FOUND, detail=PRICE_NOT_FOUND)


class InvalidPriceId(HTTPException):
    def __init__(self):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=INVALID_PRICE_ID)


class PriceApiError(HTTPException):
    def __init__(self):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=PRICE_API_ERROR)
