"""
user_profile.py
----------------
Builds and updates a User Profile vector from the user's Like/Dislike history.

Formula (report section 3.3):
    Like:    profile_new = profile_old + ALPHA * V_movie   (ALPHA = 1.0)
    Dislike: profile_new = profile_old - BETA  * V_movie   (BETA  = 0.5)
"""

import numpy as np

ALPHA = 1.0  # weight when Like
BETA = 0.5   # weight when Dislike


def build_initial_profile_from_genres(genre_vector: np.ndarray) -> np.ndarray:
    """Cold-start onboarding: new user picks genres -> initial profile.

    genre_vector: multi-hot vector, same size as movie feature vector.
                  Only the genre part is set, the rest = 0.
    Returns L2-normalized profile so cosine similarity works correctly.
    """
    genre_vector = np.asarray(genre_vector, dtype=np.float32)
    norm = np.linalg.norm(genre_vector)
    if norm == 0:
        return genre_vector.astype(np.float32)
    return (genre_vector / norm).astype(np.float32)


def update_user_profile(
    current_profile: np.ndarray,
    new_vector: np.ndarray,
    action: str,          # 'like' or 'dislike'
    alpha: float = ALPHA,
    beta: float = BETA,
) -> np.ndarray:
    """Update profile per report formula:
        Like:    profile = profile + alpha * v_movie
        Dislike: profile = profile - beta  * v_movie
    No normalization — profile magnitude reflects taste strength.
    """
    new_vector = np.asarray(new_vector, dtype=np.float32)
    if current_profile is None:
        if action == "like":
            return (alpha * new_vector).astype(np.float32)
        return None  # first-ever dislike creates no profile

    current_profile = np.asarray(current_profile, dtype=np.float32)
    if action == "like":
        updated = current_profile + alpha * new_vector
    else:
        updated = current_profile - beta * new_vector
    return updated.astype(np.float32)


def build_user_profile(liked_vectors: list, disliked_vectors: list = None) -> np.ndarray:
    """Build profile from scratch from full history (used when reloading from DB).
    Applies sequentially: start from zero vector, accumulate likes, subtract dislikes.
    """
    if not liked_vectors:
        return None

    dim = np.asarray(liked_vectors[0]).shape[0]
    profile = np.zeros(dim, dtype=np.float32)

    for v in liked_vectors:
        profile += ALPHA * np.asarray(v, dtype=np.float32)
    for v in (disliked_vectors or []):
        profile -= BETA * np.asarray(v, dtype=np.float32)

    return profile.astype(np.float32)


def make_genre_profile_vector(
    selected_genres: list,   # ['Action', 'Comedy']
    genre_labels: list,      # genre list from feature_info['genre_labels']
    total_dims: int,         # total dims of feature vector
) -> np.ndarray:
    """Create a genre (multi-hot) vector with same size as movie feature vector.
    Only the genre part (head of vector) is filled, the rest = 0.
    """
    vec = np.zeros(total_dims, dtype=np.float32)
    genre_set = set(selected_genres)
    for i, g in enumerate(genre_labels):
        if g in genre_set:
            vec[i] = 1.0
    return vec
