"""
domain/dtos.py
--------------
Cac Doi tuong Truyen tai Du lieu (Data Transfer Objects - DTOs) va Value Objects.
Giup dinh nghia hop dong du lieu (Contracts) ro rang giua cac tang:
Domain <-> Use Cases <-> Repositories <-> API Routers.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import Field

from domain.base import DomainModel


class MovieCardDTO(DomainModel):
    """Du lieu card phim tinh gon dung cho UI / Frontend."""
    movie_id: int
    title: str
    overview: str = ""
    genres: list[str] = Field(default_factory=list)
    director: Optional[str] = None
    cast: list[str] = Field(default_factory=list)
    vote_average: Optional[float] = None
    popularity: Optional[float] = None
    release_year: Optional[int] = None
    poster_url: Optional[str] = None
    match_percent: Optional[int] = None
    reasons: list[str] = Field(default_factory=list)
    reason: Optional[str] = None
    neural_used: Optional[bool] = None
    cold_start: Optional[bool] = None
    breakdown: Optional[dict[str, Any]] = None


class ScoredMovieDTO(DomainModel):
    """Phim da duoc tinh diem xep hang boi Recommender hoac Chatbot."""
    movie_id: int
    score: float = 0.0
    cosine_score: Optional[float] = None
    model_score: Optional[float] = None
    final_score: Optional[float] = None
    title: Optional[str] = None
    overview: Optional[str] = None
    genres: list[str] = Field(default_factory=list)
    director: Optional[str] = None
    cast: list[str] = Field(default_factory=list)
    vote_average: Optional[float] = None
    popularity: Optional[float] = None
    release_year: Optional[int] = None
    why: Optional[str] = None
    reasons: list[str] = Field(default_factory=list)
    reason: Optional[str] = None
    match_pct: Optional[int] = None
    match_percent: Optional[int] = None
    poster_url: Optional[str] = None
    breakdown: Optional[dict[str, Any]] = None


class RecommendationResponseDTO(DomainModel):
    """Phan hoi danh sach goi y phim cho nguoi dung."""
    user_id: Optional[str] = None
    count: int = 0
    items: list[Any] = Field(default_factory=list)
    personalized: bool = True
    cold_start: bool = False


class ChatIntentDTO(DomainModel):
    """Y dinh cua nguoi dung duoc phan tich boi Chatbot NLU."""
    wanted_genres: list[str] = Field(default_factory=list)
    avoid_genres: list[str] = Field(default_factory=list)
    similar_movie_titles: list[str] = Field(default_factory=list)
    similar_movie_ids: list[int] = Field(default_factory=list)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    max_runtime: Optional[int] = None
    director: Optional[str] = None
    actor: Optional[str] = None
    moods: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    matched_keyword_display: Optional[str] = None


class ChatbotResponseDTO(DomainModel):
    """Ket qua tra ve tu Chatbot 'Hom nay xem gi?'."""
    intent: Optional[dict[str, Any]] = None
    personalized: bool = False
    items: list[Any] = Field(default_factory=list)
    reply: str = ""
    summary: str = ""
    source: str = "local"
    query_vector: Optional[list[float]] = None


class PagedMoviesDTO(DomainModel):
    """Ket qua phan trang duyet danh sach phim."""
    page: int = 1
    page_size: int = 20
    total: int = 0
    items: list[Any] = Field(default_factory=list)


class OnboardingRequestDTO(DomainModel):
    """Yeu cau khoi tao ho so ban dau (Onboarding)."""
    genres: list[str] = Field(default_factory=list)
    favorite_movie_ids: list[int] = Field(default_factory=list)


class OnboardingResultDTO(DomainModel):
    """Ket qua sau khi onboarding."""
    ok: bool = True
    user_id: Optional[str] = None
    profile_source: str = "genres"
    seed_movie_count: int = 0
    selected_genres: list[str] = Field(default_factory=list)


class FeedbackRequestDTO(DomainModel):
    """Yeu cau danh gia Thich / Khong thich (Like / Dislike)."""
    movie_id: int
    action: str  # "like" | "dislike"


class UserHistoryItemDTO(DomainModel):
    """Lich su tuong tac cua nguoi dung."""
    movie_id: int
    action: str
    timestamp: Optional[float] = None
    title: Optional[str] = None
    poster_url: Optional[str] = None


class WatchlistResponseDTO(DomainModel):
    """Danh sach phim luu xem sau cua nguoi dung."""
    items: list[Any] = Field(default_factory=list)
