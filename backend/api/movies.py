"""
movies.py
----------
Movie API routes: get movie by ID, search, popular movies.
"""

from backend.services.movie_service import get_movie, search_movies, get_popular_movies


def movie_detail(movie_id: int, db_path: str) -> dict:
    """GET /api/movies/{movie_id}"""
    movie = get_movie(movie_id, db_path=db_path)
    if movie is None:
        raise ValueError(f"Movie {movie_id} not found.")
    return movie


def movie_search(query: str, db_path: str, limit: int = 20) -> list:
    """GET /api/movies/search?q=..."""
    return search_movies(query, db_path=db_path, limit=limit)


def popular_movies(db_path: str, limit: int = 20) -> list:
    """GET /api/movies/popular"""
    return get_popular_movies(db_path=db_path, limit=limit)
