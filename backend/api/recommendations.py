"""
recommendations.py
-------------------
Recommendations API route: get personalized recommendations for a user.
"""

from backend.services.recommendation_service import recommend_for_user


def get_recommendations(user_id: str, top_n: int, db_path: str) -> list:
    """GET /api/recommendations/{user_id}?top_n=10"""
    return recommend_for_user(user_id, top_n=top_n, db_path=db_path)
