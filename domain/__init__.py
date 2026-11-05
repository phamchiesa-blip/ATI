"""
domain/__init__.py
------------------
Goi domain cung cap cac Entity va DTO cot loi cho kien truc Clean Architecture.
"""

from domain.base import DomainModel
from domain.entities import (
    InteractionEntity,
    MovieEntity,
    UserAccountEntity,
    UserProfileEntity,
    WatchlistItemEntity,
)
from domain.dtos import (
    ChatIntentDTO,
    ChatbotResponseDTO,
    FeedbackRequestDTO,
    MovieCardDTO,
    OnboardingRequestDTO,
    OnboardingResultDTO,
    PagedMoviesDTO,
    RecommendationResponseDTO,
    ScoredMovieDTO,
    UserHistoryItemDTO,
    WatchlistResponseDTO,
)

__all__ = [
    "DomainModel",
    "MovieEntity",
    "InteractionEntity",
    "UserProfileEntity",
    "UserAccountEntity",
    "WatchlistItemEntity",
    "MovieCardDTO",
    "ScoredMovieDTO",
    "RecommendationResponseDTO",
    "ChatIntentDTO",
    "ChatbotResponseDTO",
    "PagedMoviesDTO",
    "OnboardingRequestDTO",
    "OnboardingResultDTO",
    "FeedbackRequestDTO",
    "UserHistoryItemDTO",
    "WatchlistResponseDTO",
]

