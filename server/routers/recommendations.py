from fastapi import APIRouter, Depends
from pydantic import BaseModel
from domain import FeedbackRequestDTO

from server.dependencies import current_user
from server.services.profile_service import (
    get_recommendations,
    get_user_history,
    handle_feedback,
)

router = APIRouter(tags=["Recommendations"])


class FeedbackBody(FeedbackRequestDTO):
    movie_id: int
    action: str  # "like" | "dislike"


@router.post("/api/feedback")
def feedback(body: FeedbackBody, user: dict = Depends(current_user)):
    return handle_feedback(user["id"], body.movie_id, body.action)


@router.get("/api/recommendations")
def recommendations_route(k: int = 12, mode: str = "proposed", user: dict = Depends(current_user)):
    """mode=proposed: Ranking + Neural Network cua Don. mode=baseline: chi sap theo cosine."""
    return get_recommendations(user["id"], k=k, mode=mode)


@router.get("/api/history")
def history(user: dict = Depends(current_user)):
    return get_user_history(user["id"])

