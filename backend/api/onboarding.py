"""api/onboarding.py — POST /api/onboarding handler."""

import json
import os

import numpy as np

from backend.database.database import DEFAULT_DB_PATH
from backend.services.profile_service import initialize_profile_from_onboarding

FEATURE_INFO_PATH = "feature_info.json"


def _load_genre_labels(db_path=DEFAULT_DB_PATH, feature_info_path: str = FEATURE_INFO_PATH):
    if os.path.exists(feature_info_path):
        with open(feature_info_path, encoding="utf-8") as f:
            fi = json.load(f)
        return fi.get("genre_labels", []), int(fi.get("total_dims", 0))
    # Fallback: infer from stored vectors (genre part unknown -> caller must supply)
    return [], 0


def handle_onboarding(
    user_id: str,
    selected_genres: list,  # ['Action', 'Comedy']
    db_path: str = DEFAULT_DB_PATH,
    feature_info_path: str = FEATURE_INFO_PATH,
) -> dict:
    """POST /api/onboarding"""
    genre_labels, total_dims = _load_genre_labels(db_path, feature_info_path)
    if not genre_labels or not total_dims:
        raise RuntimeError(
            f"Cannot onboard: genre_labels/total_dims missing. "
            f"Build DB via main.py to generate {feature_info_path} first."
        )
    profile = initialize_profile_from_onboarding(
        user_id=user_id,
        selected_genres=selected_genres,
        genre_labels=genre_labels,
        total_dims=total_dims,
        db_path=db_path,
    )
    return {"status": "ok", "user_id": user_id, "profile_norm": float(np.linalg.norm(profile))}
