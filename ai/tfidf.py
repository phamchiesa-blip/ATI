"""
tfidf.py
---------
TF-IDF vectorization + SVD dimensionality reduction for movie overviews.
Called by feature_engineering.py to build the text-based part of the
Movie Feature Vector.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD


def build_overview_matrix(
    overview_series,
    max_features: int = 5000,
    svd_components: int = 50,
    random_state: int = 42,
):
    """Fit TF-IDF on movie overviews, then compress with Truncated SVD.

    Parameters
    ----------
    overview_series : pd.Series of str
        Raw overview text for each movie (one entry per movie).
    max_features : int
        Maximum vocabulary size for TF-IDF.
    svd_components : int
        Target number of dimensions after SVD compression.
    random_state : int
        Seed for reproducible SVD results.

    Returns
    -------
    matrix : np.ndarray, shape (n_movies, n_components)
        Dense float32 overview vectors ready to be concatenated with other
        feature blocks.
    n_components : int
        Actual number of components used (may be < svd_components if the
        vocabulary is smaller).
    """
    tfidf = TfidfVectorizer(max_features=max_features, stop_words="english")
    tfidf_matrix = tfidf.fit_transform(overview_series)

    n_components = min(svd_components, tfidf_matrix.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=random_state)
    dense_matrix = svd.fit_transform(tfidf_matrix).astype(np.float32)

    return dense_matrix, n_components
