"""
movie.py
---------
Data model for a Movie, matching the 'movies' table in the database.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Movie:
    movie_id: int
    title: str
    overview: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    director: Optional[str] = None
    cast: List[str] = field(default_factory=list)
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    popularity: Optional[float] = None
    release_date: Optional[str] = None


@dataclass
class MovieResponse:
    """Slim response model returned to the frontend."""
    movie_id: int
    title: str
    genres: List[str]
    director: Optional[str]
    cast: List[str]
    vote_average: Optional[float]
    popularity: Optional[float]
    release_date: Optional[str]
    score: Optional[float] = None   # recommendation score, if applicable
