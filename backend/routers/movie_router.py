"""
backend/routers/movie_router.py
-------------------------------
FastAPI Router cho cac endpoint danh muc phim, tim kiem, chi tiet, trailer, overview va phim tuong tu.
"""

from typing import Optional
from fastapi import APIRouter

from backend.services.movie_service import (
    get_movie_detail,
    get_movie_overview_translated,
    get_movie_trailer,
    get_showcase_movies,
    get_similar_movies,
    list_all_genres,
    search_movies,
    suggest_entities,
)

router = APIRouter(prefix="/api", tags=["Movies"])


@router.get("/genres")
def list_genres():
    return list_all_genres()


@router.get("/showcase")
def showcase(n: int = 12):
    return get_showcase_movies(n=n)


@router.get("/suggest")
def suggest(q: str, limit: int = 4):
    return suggest_entities(q=q, limit=limit)


@router.get("/movies")
def list_movies(
    query: Optional[str] = None,
    genres: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_rating: Optional[float] = None,
    director: Optional[str] = None,
    actor: Optional[str] = None,
    voice: Optional[str] = None,
    keyword: Optional[str] = None,
    sort: str = "popularity",
    page: int = 1,
    page_size: int = 24,
):
    return search_movies(
        query=query,
        genres=genres,
        year_from=year_from,
        year_to=year_to,
        min_rating=min_rating,
        director=director,
        actor=actor,
        voice=voice,
        keyword=keyword,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/movies/{movie_id}")
def get_movie(movie_id: int):
    return get_movie_detail(movie_id=movie_id)


@router.get("/movies/{movie_id}/trailer")
def trailer(movie_id: int):
    return get_movie_trailer(movie_id=movie_id)


@router.get("/movies/{movie_id}/overview")
def overview_translated(movie_id: int, lang: str = "vi"):
    return get_movie_overview_translated(movie_id=movie_id, lang=lang)


@router.get("/movies/{movie_id}/similar")
def similar_movies(movie_id: int, k: int = 8):
    return get_similar_movies(movie_id=movie_id, k=k)


@router.post("/movies/sync-tmdb")
def sync_tmdb_catalog(
    mode: str = "recent",
    start_year: int = 2017,
    end_year: int = 2026,
    per_year: int = 10,
    limit: int = 25,
    force: bool = False,
):
    """Dong bo phim moi tu TMDB API truc tiep vao movies.db + accounts.db (giu nguyen vector 324D)."""
    from sync_tmdb import sync_movies_from_tmdb
    from backend.repositories.movie_repository import _check_db_reload
    from chatbot import get_feature_space

    res = sync_movies_from_tmdb(
        mode=mode,
        start_year=start_year,
        end_year=end_year,
        per_year=per_year,
        recent_limit=limit,
        force_update=force,
    )
    _check_db_reload()
    get_feature_space()
    return res

