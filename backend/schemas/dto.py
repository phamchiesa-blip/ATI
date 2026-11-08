"""
backend/schemas/dto.py
----------------------
Data Transfer Objects (Pydantic models) cho Request Body cua cac API endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel


class RegisterBody(BaseModel):
    email: str
    password: str
    name: str = ""
    accept_terms: bool = False


class LoginBody(BaseModel):
    email: str
    password: str


class OnboardingBody(BaseModel):
    genres: List[str] = []
    favorite_movie_ids: List[int] = []


class FeedbackBody(BaseModel):
    movie_id: int
    action: str  # "like" | "dislike"


class WatchBody(BaseModel):
    movie_id: int


class TonightBody(BaseModel):
    mood: str
    time: str = "any"
    exclude: List[int] = []


class TonightChatBody(BaseModel):
    message: str = ""
    previous_intent: Optional[dict] = None
    intent_override: Optional[dict] = None
    exclude: List[int] = []
    top_n: int = 24
    use_llm: bool = True

