from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)


class NewsSummaryRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class NewsSummaryResponse(BaseModel):
    summary: str
    reason: str


class NewsArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    time: str
    content: str
    summary: str
    reason: str
    upvote_cnt: int = 0
    is_upvoted: bool = False

    @classmethod
    def model_validate(cls, article, upvote_cnt=0, is_upvoted=False):
        return cls(
            id=article.id,
            title=article.title,
            url=article.url,
            time=article.time,
            content=article.content,
            summary=article.summary,
            reason=article.reason,
            upvote_cnt=upvote_cnt,
            is_upvoted=is_upvoted,
        )
