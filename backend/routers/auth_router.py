"""
backend/routers/auth_router.py
------------------------------
FastAPI Router cho cac endpoint xac thuc (/api/auth/*).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header

from backend.schemas.dto import LoginBody, RegisterBody
from backend.services.auth_service import (
    create_guest_session,
    current_user,
    login_account,
    logout_session,
    register_account,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/guest")
def guest():
    return create_guest_session()


@router.post("/register")
def register(body: RegisterBody, authorization: Optional[str] = Header(None)):
    return register_account(
        email_raw=body.email,
        password=body.password,
        name_raw=body.name,
        accept_terms=body.accept_terms,
        authorization=authorization,
    )


@router.post("/login")
def login(body: LoginBody):
    return login_account(email_raw=body.email, password=body.password)


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    return logout_session(authorization=authorization)

