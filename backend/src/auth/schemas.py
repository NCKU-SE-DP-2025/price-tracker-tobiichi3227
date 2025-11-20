from pydantic import BaseModel, Field


class UserAuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str

    @classmethod
    def model_validate(cls, user_obj):
        return cls(username=user_obj.username)
