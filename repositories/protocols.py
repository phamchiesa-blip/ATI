"""
protocols.py
------------
Dinh nghia cac Interface / Protocol truu tuong theo Clean Architecture.
Cac Use Case va Service chi phu thuoc vao cac Protocol nay va cac Domain Entities,
thay vi phu thuoc truc tiep vao SQLite hay co so du lieu cu the.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, Sequence, Set, Union
import numpy as np

from domain.entities import (
    InteractionEntity,
    MovieEntity,
    UserAccountEntity,
    WatchlistItemEntity,
)
from domain.dtos import PagedMoviesDTO


class MovieRepositoryProtocol(Protocol):
    """Giao dien truu tuong de truy xuat du lieu phim va feature vectors."""

    def get_vector(self, movie_id: int) -> Optional[np.ndarray]:
        """Lay vector dac trung (324 chieu) cua phim."""
        ...

    def get_all_vectors(self) -> tuple[np.ndarray, np.ndarray]:
        """Lay toan bo movie_ids va ma tran vectors (N x 324)."""
        ...

    def get_metadata(self, movie_id: int) -> Optional[Union[MovieEntity, dict[str, Any]]]:
        """Lay thong tin chi tiet (title, genres, director, cast, vote...)."""
        ...

    def get_popular_movies(
        self,
        limit: int = 10,
        min_vote_count: int = 500,
        min_vote_average: float = 6.5,
        exclude_ids: Optional[Set[int]] = None,
        exclude_genres: Optional[Set[str]] = None,
    ) -> list[Union[MovieEntity, dict[str, Any]]]:
        """Lay danh sach phim pho bien, ho tro loc tru cac phim va the loai ghet."""
        ...

    def list_movies(
        self,
        page: int = 1,
        page_size: int = 20,
        genre: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Union[PagedMoviesDTO, dict[str, Any]]:
        """Duyet danh sach phim co phan trang va tim kiem."""
        ...

    def get_all_movie_rows(self) -> list[Union[MovieEntity, dict[str, Any]]]:
        """Lay toan bo metadata phim sap xep theo movie_id phuc vu index."""
        ...

    def get_keywords_mapping(self) -> dict[int, list[str]]:
        """Lay ban do movie_id -> danh sach tu khoa TMDB."""
        ...

    def get_onboarding_candidates(self) -> list[Union[MovieEntity, dict[str, Any]]]:
        """Lay danh sach phim sap xep theo do pho bien phuc vu onboarding."""
        ...


class InteractionRepositoryProtocol(Protocol):
    """Giao dien truu tuong cho viec luu tru va doc lich su Like / Dislike."""

    def log_interaction(self, user_id: str, movie_id: int, action: str) -> None:
        """Ghi mot luot Like hoac Dislike vao lich su."""
        ...

    def get_interactions(self, user_id: str) -> list[Union[InteractionEntity, dict[str, Any]]]:
        """Lay toan bo lich su tuong tac cua user theo thu tu thoi gian."""
        ...

    def delete_interactions(self, user_id: str) -> None:
        """Xoa toan bo lich su tuong tac cua user khi reset profile."""
        ...


class AccountRepositoryProtocol(Protocol):
    """Giao dien truu tuong cho quan ly tai khoan, phien dang nhap va onboarding."""

    def get_by_email(self, email: str) -> Optional[Union[UserAccountEntity, dict[str, Any]]]:
        ...

    def get_by_id(self, user_id: str) -> Optional[Union[UserAccountEntity, dict[str, Any]]]:
        ...

    def create_guest_account(
        self, user_id: str, email: str, name: str, salt: bytes, password_hash: bytes, created_at: float
    ) -> None:
        ...

    def create_user_account(
        self, user_id: str, email: str, name: str, salt: bytes, password_hash: bytes, created_at: float
    ) -> None:
        ...

    def upgrade_guest_account(
        self, user_id: str, email: str, name: str, salt: bytes, password_hash: bytes
    ) -> None:
        ...

    def create_session(self, token_hash: str, user_id: str, expires_at: float) -> None:
        ...

    def get_account_by_session(self, token_hash: str, current_time: float) -> Optional[Union[UserAccountEntity, dict[str, Any]]]:
        ...

    def delete_session(self, token_hash: str) -> None:
        ...

    def delete_user_sessions(self, user_id: str) -> None:
        ...

    def get_onboarding(self, user_id: str) -> Optional[dict[str, Any]]:
        ...

    def save_onboarding(self, user_id: str, genres_json: str, favorites_json: str) -> None:
        ...

    def reset_onboarding(self, user_id: str) -> None:
        ...


class WatchlistRepositoryProtocol(Protocol):
    """Giao dien truu tuong cho danh sach xem sau cua nguoi dung."""

    def get_watchlist(self, user_id: str) -> list[Union[WatchlistItemEntity, dict[str, Any]]]:
        ...

    def add_to_watchlist(self, user_id: str, movie_id: int, added_at: float) -> None:
        ...

    def remove_from_watchlist(self, user_id: str, movie_id: int) -> None:
        ...
