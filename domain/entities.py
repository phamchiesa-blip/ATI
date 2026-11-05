"""
domain/entities.py
------------------
Cac Thuc the mien (Domain Entities) theo kien truc Clean Architecture.
Chua cac quy tac va mo hinh du lieu cot loi cua he thong Recommender,
hoan toan doc lap voi framework web (FastAPI) va he co so du lieu (SQLite).
"""

from __future__ import annotations

import json
from typing import Any, Optional
from pydantic import Field, field_validator

from domain.base import DomainModel


class MovieEntity(DomainModel):
    """Thuc the Phim cot loi (Core Movie Entity)."""
    movie_id: int
    title: str
    overview: str = ""
    genres: list[str] = Field(default_factory=list)
    release_date: Optional[str] = None
    release_year: Optional[int] = None
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    director: Optional[str] = None
    cast: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    runtime: Optional[int] = None
    revenue: Optional[int] = None
    budget: Optional[int] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None

    @field_validator("genres", "cast", "keywords", mode="before")
    @classmethod
    def _parse_json_list(cls, v: Any) -> list:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [v] if v.strip() else []
        return v if isinstance(v, list) else []

    @field_validator("release_year", mode="before")
    @classmethod
    def _infer_year(cls, v: Any, info) -> Optional[int]:
        if v is not None:
            try:
                return int(v)
            except (ValueError, TypeError):
                pass
        rel_date = info.data.get("release_date") or ""
        if len(rel_date) >= 4 and rel_date[:4].isdigit():
            return int(rel_date[:4])
        return None


class InteractionEntity(DomainModel):
    """Thuc the Tuong tac nguoi dung (Like / Dislike)."""
    movie_id: int
    action: str  # "like" | "dislike"
    user_id: Optional[str] = None
    timestamp: float = 0.0
    created_at: Optional[str] = None


class UserProfileEntity(DomainModel):
    """Thuc the Ho so nguoi dung (User Profile & Vector)."""
    user_id: str
    vector: Optional[Any] = None  # numpy.ndarray (324-D) hoac list[float]
    like_count: int = 0
    dislike_count: int = 0
    updated_at: float = 0.0

    def is_initialized(self) -> bool:
        return self.vector is not None and (self.like_count > 0 or self.dislike_count > 0)


class UserAccountEntity(DomainModel):
    """Thuc the Tai khoan nguoi dung."""
    id: Optional[str] = None
    user_id: Optional[str] = None
    email: str
    name: str = ""
    onboarded: bool = False
    is_guest: bool = False
    created_at: float = 0.0

    @property
    def uid(self) -> str:
        return self.user_id or self.id or ""


class WatchlistItemEntity(DomainModel):
    """Thuc the Danh sach xem sau (Watchlist)."""
    user_id: Optional[str] = None
    movie_id: int
    added_at: float = 0.0
