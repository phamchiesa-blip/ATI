from typing import List, Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from domain import DomainModel, OnboardingRequestDTO

from server.dependencies import current_user
from server.services.auth_service import (
    create_guest_session,
    login_account,
    logout_account,
    register_account,
)
from server.services.profile_service import (
    add_watchlist,
    get_selection,
    get_watchlist,
    handle_onboarding,
    remove_watchlist,
    reset_user_profile,
)

router = APIRouter(tags=["Auth & Profile"])


class RegisterBody(DomainModel):
    email: str
    password: str
    name: str = ""
    accept_terms: bool = False


class LoginBody(DomainModel):
    email: str
    password: str


class OnboardingBody(OnboardingRequestDTO):
    genres: List[str] = []
    favorite_movie_ids: List[int] = []


class WatchBody(DomainModel):
    movie_id: int


@router.post("/api/auth/guest")
def guest():
    """Tao phien khach: dung duoc moi tinh nang, du lieu gan voi phien nay.
    Neu sau do dang ky, tai khoan khach duoc nang cap (giu nguyen ho so + lich su)."""
    return create_guest_session()


@router.post("/api/auth/register")
def register(body: RegisterBody, authorization: Optional[str] = Header(None)):
    return register_account(
        email=body.email,
        password=body.password,
        name=body.name,
        accept_terms=body.accept_terms,
        authorization=authorization,
    )


@router.post("/api/auth/login")
def login(body: LoginBody):
    return login_account(email=body.email, password=body.password)


@router.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return user


@router.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    return logout_account(authorization)


@router.post("/api/onboarding")
def onboarding(body: OnboardingBody, user: dict = Depends(current_user)):
    return handle_onboarding(user["id"], body.genres, body.favorite_movie_ids)


@router.get("/api/onboarding")
def get_onboarding(user: dict = Depends(current_user)):
    sel = get_selection(user["id"]) or {"genres": [], "favorites": []}
    return sel


@router.delete("/api/me/profile")
def reset_profile(user: dict = Depends(current_user)):
    """Xoa profile + lich su Like/Dislike de lam lai tu dau (khong xoa tai khoan)."""
    return reset_user_profile(user["id"])


@router.get("/api/watchlist")
def get_user_watchlist(user: dict = Depends(current_user)):
    return get_watchlist(user["id"])


@router.post("/api/watchlist")
def add_user_watchlist(body: WatchBody, user: dict = Depends(current_user)):
    return add_watchlist(user["id"], body.movie_id)


@router.delete("/api/watchlist/{movie_id}")
def remove_user_watchlist(movie_id: int, user: dict = Depends(current_user)):
    return remove_watchlist(user["id"], movie_id)

