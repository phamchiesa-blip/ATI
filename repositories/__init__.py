"""
repositories package
--------------------
Chua cac Interface / Protocol va cac ban cai dat Repository theo Clean Architecture.
"""

from repositories.protocols import (
    AccountRepositoryProtocol,
    InteractionRepositoryProtocol,
    MovieRepositoryProtocol,
    WatchlistRepositoryProtocol,
)
from repositories.sqlite_movie_repo import SqliteMovieRepository
from repositories.sqlite_interaction_repo import SqliteInteractionRepository
from repositories.sqlite_account_repo import SqliteAccountRepository
from repositories.sqlite_watchlist_repo import SqliteWatchlistRepository
from repositories.in_memory_repo import InMemoryMovieRepository, InMemoryInteractionRepository

__all__ = [
    "MovieRepositoryProtocol",
    "InteractionRepositoryProtocol",
    "AccountRepositoryProtocol",
    "WatchlistRepositoryProtocol",
    "SqliteMovieRepository",
    "SqliteInteractionRepository",
    "SqliteAccountRepository",
    "SqliteWatchlistRepository",
    "InMemoryMovieRepository",
    "InMemoryInteractionRepository",
]

