from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SubjectIn(BaseModel):
    year: str = Field(min_length=1)
    subject: str = Field(min_length=1)


class AskRequest(SubjectIn):
    question: str = Field(min_length=2)
    explanation_mode: bool = False


class SummaryRequest(SubjectIn):
    focus: str | None = None


class NotesRequest(SubjectIn):
    focus: str | None = None


class QuizRequest(SubjectIn):
    topic: str = Field(min_length=2)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    num_questions: int = Field(default=5, ge=1, le=15)


class SourceItem(BaseModel):
    filename: str
    page: int
    chunk_index: int
    score: float


class GenerationResponse(BaseModel):
    content: str
    sources: list[SourceItem]
    cached: bool


class FeedItem(BaseModel):
    id: int
    year: str
    subject: str
    content_type: str
    query_text: str | None
    difficulty: str | None
    explanation_mode: bool
    content: str
    sources: list[SourceItem]
    is_cached: bool
    created_at: datetime


class FeedResponse(BaseModel):
    items: list[FeedItem]
