from typing import Optional

from fastapi import APIRouter

from server.services.movie_service import (
    get_genres_distribution,
    get_movie_detail,
    get_movie_trailer,
    get_showcase,
    get_similar_movies,
    query_movies,
    suggest_entities,
)

router = APIRouter(tags=["Movies"])


@router.get("/api/genres")
def list_genres():
    return get_genres_distribution()


@router.get("/api/showcase")
def showcase(n: int = 12):
    """Phim ngau nhien (trong nhom noi tieng, diem cao) cho trang dang nhap."""
    return get_showcase(n=n)


@router.get("/api/suggest")
def suggest(q: str, limit: int = 4):
    return suggest_entities(q=q, limit=limit)


@router.get("/api/movies")
def list_movies_route(
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
    return query_movies(
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


@router.get("/api/movies/{movie_id}")
def get_movie(movie_id: int):
    return get_movie_detail(movie_id)


@router.get("/api/movies/{movie_id}/trailer")
def trailer(movie_id: int):
    """Khoa video YouTube cua trailer (tu bang tmdb_cache, hoac goi TMDB neu co key)."""
    return get_movie_trailer(movie_id)


@router.get("/api/movies/{movie_id}/similar")
def similar_movies(movie_id: int, k: int = 8):
    """Phim co noi dung gan nhat (cosine giua vector phim nay va toan bo phim khac)."""
    return get_similar_movies(movie_id, k=k)

