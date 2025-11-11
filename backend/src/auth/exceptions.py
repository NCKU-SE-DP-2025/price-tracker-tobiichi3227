from http import HTTPStatus

from fastapi import HTTPException

from src.auth.constants import (
    INVALID_CREDENTIALS,
    INVALID_TOKEN,
    USER_ALREADY_EXISTS,
    USER_NOT_FOUND,
)


class UserAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=USER_ALREADY_EXISTS)


class InvalidCredentials(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=HTTPStatus.UNAUTHORIZED, detail=INVALID_CREDENTIALS
        )


class UserNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=HTTPStatus.UNAUTHORIZED, detail=USER_NOT_FOUND)


class InvalidToken(HTTPException):
    def __init__(self):
        super().__init__(status_code=HTTPStatus.UNAUTHORIZED, detail=INVALID_TOKEN)
