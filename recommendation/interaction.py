"""
interaction.py
--------------
Luu lich su tuong tac (Like/Dislike) cua user vao DB thong qua API
cua Data team (feature_store.log_interaction).

Luong xu ly:
    user_id + movie_id + interaction_type
           |
           v
    log_interaction(user_id, movie_id, action, db_path)
           |
           v
    user_interaction_history (SQLite table)

Schema luu tru (duoc Data team tao san):
    interaction_id  INTEGER  PRIMARY KEY AUTOINCREMENT
    user_id         TEXT     NOT NULL
    movie_id        INTEGER  NOT NULL
    action          TEXT     NOT NULL  (like / dislike)
    created_at      TEXT     NOT NULL  (ISO-8601 UTC)
"""

from __future__ import annotations

import sys
import os

# Cho phep import feature_store tu thu muc data_module/src
_DATA_MODULE_SRC = os.path.join(
    os.path.dirname(__file__), "..", "data_module", "src"
)
sys.path.insert(0, os.path.abspath(_DATA_MODULE_SRC))

from feature_store import log_interaction as _log, get_user_interactions as _get


def save_interaction(
    user_id: str,
    movie_id: int,
    interaction: str,
    db_path: str = "movies.db",
) -> None:
    """Ghi 1 luot Like/Dislike vao User Interaction History.

    Parameters
    ----------
    user_id : str
        ID cua user.
    movie_id : int
        ID cua phim.
    interaction : str
        'like' hoac 'dislike'.
    db_path : str
        Duong dan den file SQLite (mac dinh 'movies.db').

    Raises
    ------
    ValueError
        Neu interaction khong phai 'like' hoac 'dislike'.
    """
    if interaction not in ("like", "dislike"):
        raise ValueError(f"interaction phai la 'like' hoac 'dislike', nhan duoc: {interaction!r}")
    _log(user_id, movie_id, interaction, db_path=db_path)


def get_interactions(
    user_id: str,
    db_path: str = "movies.db",
) -> list[dict]:
    """Lay toan bo lich su tuong tac cua user (cu nhat truoc).

    Returns
    -------
    list[dict]
        Moi phan tu co dang:
        {
            "movie_id":   int,
            "action":     "like" | "dislike",
            "created_at": str  (ISO-8601),
        }
    """
    return _get(user_id, db_path=db_path)
