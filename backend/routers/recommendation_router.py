"""
backend/routers/recommendation_router.py
----------------------------------------
FastAPI Router cho Ho so so thich, Goi y ca nhan hoa, Watchlist va 'Hom nay xem gi?' (Chat Bot & Mood).
"""

from fastapi import APIRouter, Depends

from backend.schemas.dto import (
    FeedbackBody,
    OnboardingBody,
    TonightBody,
    TonightChatBody,
    WatchBody,
)
from backend.services.auth_service import current_user
from backend.services.recommendation_service import (
    add_to_watchlist,
    delete_feedback,
    get_interaction_history,
    get_onboarding_selection,
    get_tonight_options,
    get_user_recommendations,
    list_watchlist,
    recommend_tonight_by_mood,
    recommend_tonight_chat,
    record_feedback,
    remove_from_watchlist,
    reset_user_profile,
    save_onboarding,
)

router = APIRouter(prefix="/api", tags=["Recommendations & User Profile"])


@router.post("/onboarding")
def onboarding(body: OnboardingBody, user: dict = Depends(current_user)):
    return save_onboarding(
        user_id=user["id"],
        genres=body.genres,
        favorite_movie_ids=body.favorite_movie_ids,
    )


@router.get("/onboarding")
def get_onboarding(user: dict = Depends(current_user)):
    return get_onboarding_selection(user["id"]) or {"genres": [], "favorites": []}


@router.post("/feedback")
def feedback(body: FeedbackBody, user: dict = Depends(current_user)):
    return record_feedback(user_id=user["id"], movie_id=body.movie_id, action=body.action)


@router.delete("/feedback/{movie_id}")
def remove_feedback(movie_id: int, user: dict = Depends(current_user)):
    return delete_feedback(user_id=user["id"], movie_id=movie_id)


@router.get("/recommendations")
def recommendations(k: int = 12, mode: str = "proposed", user: dict = Depends(current_user)):
    return get_user_recommendations(user_id=user["id"], k=k, mode=mode)


@router.get("/history")
def history(user: dict = Depends(current_user)):
    return get_interaction_history(user_id=user["id"])


@router.delete("/me/profile")
def reset_profile(user: dict = Depends(current_user)):
    return reset_user_profile(user_id=user["id"])


@router.get("/watchlist")
def get_watchlist(user: dict = Depends(current_user)):
    return list_watchlist(user_id=user["id"])


@router.post("/watchlist")
def add_watchlist(body: WatchBody, user: dict = Depends(current_user)):
    return add_to_watchlist(user_id=user["id"], movie_id=body.movie_id)


@router.delete("/watchlist/{movie_id}")
def remove_watchlist(movie_id: int, user: dict = Depends(current_user)):
    return remove_from_watchlist(user_id=user["id"], movie_id=movie_id)


@router.get("/tonight/options")
def tonight_options():
    return get_tonight_options()


@router.post("/tonight/chat")
def tonight_chat(body: TonightChatBody, user: dict = Depends(current_user)):
    return recommend_tonight_chat(
        user_id=user["id"],
        message=body.message,
        previous_intent=body.previous_intent,
        intent_override=body.intent_override,
        exclude=body.exclude,
        top_n=body.top_n,
        use_llm=body.use_llm,
    )


@router.post("/tonight")
def tonight(body: TonightBody, user: dict = Depends(current_user)):
    return recommend_tonight_by_mood(
        user_id=user["id"],
        mood_id=body.mood,
        time_id=body.time,
        exclude=body.exclude,
    )

