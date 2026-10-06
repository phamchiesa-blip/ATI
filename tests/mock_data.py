# tests/mock_data.py — use when movies.db is not available yet
import random

import numpy as np

N_FEATURES = 320   # expected total dims (20 genre + 51 director + 200 cast + 50 overview + 3 numeric)
N_MOVIES = 100


def make_mock_matrix():
    np.random.seed(42)
    ids = np.arange(1, N_MOVIES + 1)
    matrix = np.random.rand(N_MOVIES, N_FEATURES).astype(np.float32)
    return ids, matrix


def make_mock_metadata():
    genres_pool = ["Action", "Comedy", "Drama", "Horror", "Sci-Fi"]
    return {
        i: {
            "title": f"Mock Movie {i}",
            "genres": random.sample(genres_pool, k=2),
            "vote_average": round(random.uniform(5, 9), 1),
            "popularity": random.uniform(10, 200),
            "release_date": f"{random.randint(2000, 2023)}-01-01",
        }
        for i in range(1, N_MOVIES + 1)
    }
