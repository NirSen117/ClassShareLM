from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# --- Auth ---
class UserResponse(BaseModel):
    id: int
    firebase_uid: str
    email: str
    display_name: str
    photo_url: str | None = None


# --- Section ---
class SectionIn(BaseModel):
    year: str = Field(min_length=1)
    name: str = Field(min_length=1)


class SectionResponse(BaseModel):
    id: int
    year: str
    name: str


# --- Subject ---
class SubjectIn(BaseModel):
    year: str = Field(min_length=1)
    section: str = Field(min_length=1)
    subject: str = Field(min_length=1)


# --- Generation Requests ---
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


# --- Sources ---
class SourceItem(BaseModel):
    filename: str
    page: int
    chunk_index: int
    score: float


# --- Generation Response ---
class GenerationResponse(BaseModel):
    content: str
    sources: list[SourceItem]
    cached: bool


# --- Feed ---
class FeedItem(BaseModel):
    id: int
    year: str
    section: str
    subject: str
    content_type: str
    query_text: str | None
    difficulty: str | None
    explanation_mode: bool
    content: str
    sources: list[SourceItem]
    is_cached: bool
    created_at: datetime
    user_display_name: str = "Anonymous"
    user_photo_url: str | None = None


class FeedResponse(BaseModel):
    my_items: list[FeedItem]
    public_items: list[FeedItem]
