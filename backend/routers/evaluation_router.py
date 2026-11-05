"""
backend/routers/evaluation_router.py
------------------------------------
FastAPI Router cho endpoint Danh gia he thong (/api/evaluation).
"""

from fastapi import APIRouter

from backend.services.evaluation_service import get_evaluation_report

router = APIRouter(prefix="/api", tags=["Evaluation"])


@router.get("/evaluation")
def evaluation():
    return get_evaluation_report()

