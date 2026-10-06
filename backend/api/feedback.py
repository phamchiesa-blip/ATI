"""
feedback.py
------------
Feedback API routes: submit like/dislike interactions.
"""

from backend.database.database import log_interaction, get_user_interactions, DEFAULT_DB_PATH
from backend.services.profile_service import process_feedback_and_update


def submit_feedback(user_id: str, movie_id: int, action: str, db_path: str = DEFAULT_DB_PATH) -> dict:
    """POST /api/feedback — log like/dislike and update profile immediately."""
    log_interaction(user_id, movie_id, action, db_path=db_path)
    process_feedback_and_update(user_id, movie_id, action, db_path=db_path)
    return {"status": "ok", "user_id": user_id, "movie_id": movie_id, "action": action}


def get_feedback(user_id: str, db_path: str = DEFAULT_DB_PATH) -> list:
    """GET /api/feedback/{user_id}"""
    return get_user_interactions(user_id, db_path=db_path)
