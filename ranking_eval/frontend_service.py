"""Backend-facing service functions for the Frontend team.

These functions define JSON-friendly inputs/outputs without choosing a web
framework. A FastAPI/Flask route can call them directly. Data is read from the
Part I SQLite store; Like/Dislike and profile seeding use Part II public APIs;
recommendations use Part III ranking.
"""

from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DATA_SRC = os.path.join(_ROOT, "data_module", "src")
_RECOMMENDATION = os.path.join(_ROOT, "recommendation")
for _path in (_ROOT, _DATA_SRC, _RECOMMENDATION):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from feature_store import DEFAULT_DB_PATH, check_db_exists, get_movie_metadata
from repositories.protocols import MovieRepositoryProtocol, InteractionRepositoryProtocol
from repositories.sqlite_movie_repo import SqliteMovieRepository
from repositories.sqlite_interaction_repo import SqliteInteractionRepository
from domain import MovieEntity, PagedMoviesDTO, OnboardingResultDTO, RecommendationResponseDTO
from recommender import (
    dislike as core_dislike,
    like as core_like,
    seed_profile_from_onboarding,
)

from .integration import get_ranked_recommendations

DEFAULT_ONBOARDING_TOP_N: int = 8


def _decode_movie(row):
    item = dict(row)
    raw_genres = item.get("genres")
    item["genres"] = raw_genres if isinstance(raw_genres, list) else json.loads(raw_genres or "[]")
    raw_cast = item.get("cast")
    item["cast"] = raw_cast if isinstance(raw_cast, list) else json.loads(raw_cast or "[]")
    date = item.get("release_date") or ""
    if date[:4].isdigit():
        item["release_year"] = int(date[:4])
    return MovieEntity.from_dict(item)


def get_popular_movies(
    *,
    db_path: str,
    limit: int = 10,
    min_vote_count: int = 500,
    min_vote_average: float = 6.5,
    exclude_ids: set[int] | None = None,
    exclude_genres: set[str] | None = None,
    movie_repo: MovieRepositoryProtocol | None = None,
) -> list[dict]:
    """Retrieve popular and well-rated movies via MovieRepositoryProtocol."""
    repo = movie_repo or SqliteMovieRepository(db_path=db_path)
    return repo.get_popular_movies(
        limit=limit,
        min_vote_count=min_vote_count,
        min_vote_average=min_vote_average,
        exclude_ids=exclude_ids,
        exclude_genres=exclude_genres,
    )


def list_movies(
    *,
    db_path: str,
    page: int = 1,
    page_size: int = 20,
    genre: str | None = None,
    search: str | None = None,
    movie_repo: MovieRepositoryProtocol | None = None,
) -> dict:
    """Browse movies with pagination and optional exact genre/title filters via MovieRepositoryProtocol."""
    repo = movie_repo or SqliteMovieRepository(db_path=db_path)
    return repo.list_movies(
        page=page,
        page_size=page_size,
        genre=genre,
        search=search,
    )


def onboard_user(
    user_id: str,
    *,
    db_path: str,
    selected_genres: list[str] | None = None,
    favorite_movie_ids: list[int] | None = None,
    top_n_per_genre: int = DEFAULT_ONBOARDING_TOP_N,
    movie_repo: MovieRepositoryProtocol | None = None,
) -> dict:
    """Seed Part II's initial profile from favorite movies or chosen genres."""
    repo = movie_repo or SqliteMovieRepository(db_path=db_path)
    genres = [genre.strip() for genre in (selected_genres or []) if genre.strip()]
    movie_ids = list(dict.fromkeys(int(mid) for mid in (favorite_movie_ids or [])))
    source = "favorite_movies"
    if not movie_ids and genres:
        rows = repo.get_onboarding_candidates()
        merged_ids = []
        for genre in genres:
            wanted = genre.casefold()
            genre_found = 0
            for row in rows:
                stored_genres = [g.casefold() for g in (row["genres"] if isinstance(row["genres"], list) else json.loads(row["genres"] or "[]"))]
                if wanted in stored_genres:
                    merged_ids.append(int(row["movie_id"]))
                    genre_found += 1
                    if genre_found >= top_n_per_genre:
                        break

        # Deduplicate while preserving deterministic order
        movie_ids = list(dict.fromkeys(merged_ids))
        source = "selected_genres"

    if not movie_ids:
        raise ValueError("Choose at least one genre or favorite movie to start a profile")
    valid_ids = [mid for mid in movie_ids if repo.get_metadata(mid) is not None]
    if not valid_ids:
        raise ValueError("None of the selected movies exist in the movie database")

    seed_profile_from_onboarding(user_id, valid_ids, db_path=db_path, movie_repo=repo)
    return OnboardingResultDTO(

        ok=True,

        user_id=user_id,

        profile_source=source,

        seed_movie_count=len(valid_ids),

        selected_genres=genres,

    )


def record_interaction(
    user_id: str,
    movie_id: int,
    action: str,
    *,
    db_path: str,
    preserve_numeric_dislikes: bool = False,
) -> dict:
    """Pass Like/Dislike to Part II, which updates profile and stores history."""
    if action not in ("like", "dislike"):
        raise ValueError("action must be 'like' or 'dislike'")
    if get_movie_metadata(int(movie_id), db_path=db_path) is None:
        raise ValueError(f"movie_id={movie_id} does not exist")
    if action == "like":
        core_like(user_id, int(movie_id), db_path=db_path)
    else:
        core_dislike(
            user_id,
            int(movie_id),
            db_path=db_path,
            preserve_numeric=preserve_numeric_dislikes,
        )
    return {"ok": True, "user_id": user_id, "movie_id": int(movie_id), "action": action}


def recommendations(
    user_id: str,
    *,
    db_path: str = DEFAULT_DB_PATH,
    limit: int = 10,
    candidate_k: int = 100,
) -> dict:
    """Return a JSON-friendly ranked list for the View Recommendations screen."""
    if limit < 1 or candidate_k < limit:
        raise ValueError("Require limit >= 1 and candidate_k >= limit")
    items = get_ranked_recommendations(
        user_id,
        candidate_k=candidate_k,
        top_n=limit,
        db_path=db_path,
    )
    return RecommendationResponseDTO(

        user_id=user_id,

        count=len(items),

        items=items,

    )
