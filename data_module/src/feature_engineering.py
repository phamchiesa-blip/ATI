"""
feature_engineering.py
-----------------------
Step 2: turn the cleaned movie table (from data_pipeline.py) into one
numeric "Movie Feature Vector" per movie, combining:

    Genre      -> multi-hot over all genres
    Director   -> one-hot over the most frequent directors (+ "Other")
    Cast       -> multi-hot over the most frequent actors (+ nothing for rare ones)
    Overview   -> TF-IDF text vector, compressed with SVD to a fixed size
    Rating, Popularity, Release Year -> scaled to [0, 1]

All pieces are scaled to a similar range before being concatenated, so no
single piece (e.g. a huge TF-IDF vector) silently dominates the Cosine
Similarity that Son's module will compute on top of this.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer, MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD


@dataclass
class FeatureConfig:
    top_k_directors: int = 50
    top_k_cast: int = 200
    tfidf_max_features: int = 5000
    overview_svd_components: int = 50
    random_state: int = 42


def _top_k_values(list_column, k):
    """Given a pandas Series of lists (e.g. cast_list), return the k most
    frequent individual values across the whole dataset."""
    from collections import Counter

    counter = Counter()
    for values in list_column:
        counter.update(values)
    return [name for name, _ in counter.most_common(k)]


def _one_hot_director(director_series, top_directors):
    """One-hot encode director, bucketing every director outside the
    top-K into a single 'Other' column so the matrix doesn't explode with
    ~2000 near-unique directors."""
    top_set = set(top_directors)
    categories = top_directors + ["Other/Unknown"]
    matrix = np.zeros((len(director_series), len(categories)), dtype=np.float32)
    col_index = {name: i for i, name in enumerate(categories)}
    for row, director in enumerate(director_series):
        key = director if director in top_set else "Other/Unknown"
        matrix[row, col_index[key]] = 1.0
    return matrix, categories


def _multi_hot_cast(cast_series, top_cast):
    """Multi-hot encode cast members, keeping only the most frequent actors.
    Movies whose cast doesn't overlap the top-K just get an all-zero cast
    vector -- the other feature pieces (genre, overview, director...) still
    carry signal for them."""
    top_set = set(top_cast)
    col_index = {name: i for i, name in enumerate(top_cast)}
    matrix = np.zeros((len(cast_series), len(top_cast)), dtype=np.float32)
    for row, cast in enumerate(cast_series):
        for actor in cast:
            if actor in top_set:
                matrix[row, col_index[actor]] = 1.0
    return matrix


def build_feature_vectors(df, config: FeatureConfig = FeatureConfig()):
    """Build the final Movie Feature Vector matrix.

    Returns
    -------
    movie_ids : np.ndarray, shape (n_movies,)
        movie_id for each row, in the same order as `vectors`.
    vectors : np.ndarray, shape (n_movies, n_features)
        the combined, normalized feature vector for each movie.
    feature_info : dict
        column boundaries + fitted encoders, kept in case a later step
        needs to know which columns are "genre", which are "overview", etc.
        (not required for basic use -- get_movie_vector() only needs `vectors`).
    """
    # --- Genre: multi-hot over every genre that appears in the dataset ---
    genre_binarizer = MultiLabelBinarizer()
    genre_matrix = genre_binarizer.fit_transform(df["genres_list"]).astype(np.float32)

    # --- Director: one-hot over the most frequent directors ---
    top_directors = _top_k_values(df["director"].apply(lambda d: [d] if d else []),
                                   config.top_k_directors)
    director_matrix, director_categories = _one_hot_director(df["director"], top_directors)

    # --- Cast: multi-hot over the most frequent actors ---
    top_cast = _top_k_values(df["cast_list"], config.top_k_cast)
    cast_matrix = _multi_hot_cast(df["cast_list"], top_cast)

    # --- Overview: TF-IDF, then compress to a fixed-size dense vector ---
    tfidf = TfidfVectorizer(max_features=config.tfidf_max_features, stop_words="english")
    tfidf_matrix = tfidf.fit_transform(df["overview"])
    n_components = min(config.overview_svd_components, tfidf_matrix.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=config.random_state)
    overview_matrix = svd.fit_transform(tfidf_matrix).astype(np.float32)

    # --- Numeric signals: Rating, Popularity, Release Year -> scaled [0, 1] ---
    numeric_raw = df[["vote_average", "popularity", "release_year"]].copy()
    numeric_raw["release_year"] = numeric_raw["release_year"].fillna(numeric_raw["release_year"].median())
    scaler = MinMaxScaler()
    numeric_matrix = scaler.fit_transform(numeric_raw).astype(np.float32)

    # --- Concatenate every piece into one vector per movie ---
    vectors = np.hstack([
        genre_matrix,
        director_matrix,
        cast_matrix,
        overview_matrix,
        numeric_matrix,
    ]).astype(np.float32)

    feature_info = {
        "genre_labels": list(genre_binarizer.classes_),
        "director_labels": director_categories,
        "cast_labels": top_cast,
        "overview_dims": n_components,
        "numeric_labels": ["vote_average", "popularity", "release_year"],
        "column_ranges": {
            "genre": (0, genre_matrix.shape[1]),
            "director": (genre_matrix.shape[1], genre_matrix.shape[1] + director_matrix.shape[1]),
            "cast": (genre_matrix.shape[1] + director_matrix.shape[1],
                     genre_matrix.shape[1] + director_matrix.shape[1] + cast_matrix.shape[1]),
        },
        "total_dims": vectors.shape[1],
    }

    return df["movie_id"].to_numpy(), vectors, feature_info
