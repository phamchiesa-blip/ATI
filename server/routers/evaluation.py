from fastapi import APIRouter

from server.services.evaluation_service import get_evaluation_data

router = APIRouter(tags=["Evaluation"])


@router.get("/api/evaluation")
def evaluation():
    return get_evaluation_data()

