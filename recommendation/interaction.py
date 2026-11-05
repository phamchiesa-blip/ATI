"""
interaction.py
--------------
Luu lich su tuong tac (Like/Dislike) cua user vao DB thong qua Repository Abstraction
theo Clean Architecture.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_MODULE_SRC = os.path.join(_ROOT, "data_module", "src")
for _p in (_ROOT, _DATA_MODULE_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from feature_store import DEFAULT_DB_PATH
from repositories.protocols import InteractionRepositoryProtocol
from repositories.sqlite_interaction_repo import SqliteInteractionRepository


def save_interaction(
    user_id: str,
    movie_id: int,
    interaction: str,
    db_path: str = DEFAULT_DB_PATH,
    repository: Optional[InteractionRepositoryProtocol] = None,
) -> None:
    """Ghi 1 luot Like/Dislike vao User Interaction History."""
    repo = repository or SqliteInteractionRepository(db_path=db_path)
    repo.log_interaction(user_id, movie_id, interaction)


def get_interactions(
    user_id: str,
    db_path: str = DEFAULT_DB_PATH,
    repository: Optional[InteractionRepositoryProtocol] = None,
) -> list[dict]:
    """Lay toan bo lich su tuong tac cua user (cu nhat truoc)."""
    repo = repository or SqliteInteractionRepository(db_path=db_path)
    return repo.get_interactions(user_id)
