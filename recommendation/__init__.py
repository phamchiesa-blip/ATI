"""
recommendation/
---------------
Recommendation Core - Content-Based Filtering.

Public API:
    from recommendation.recommender import like, dislike, recommend, seed_profile_from_onboarding
    from recommendation.similarity import cosine_similarity, get_top_k_movies
    from recommendation.interaction import save_interaction, get_interactions
    from recommendation.user_profile import UserProfile, UserProfileRegistry
"""
from .recommender import like, dislike, recommend, seed_profile_from_onboarding

__all__ = ["like", "dislike", "recommend", "seed_profile_from_onboarding"]
