from typing import Optional

from fastapi import Header, HTTPException

from server.services.auth_service import public_user, row_from_token


def current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency xac thuc nguoi dung tu Authorization header."""
    row = row_from_token(authorization)
    if row is None:
        raise HTTPException(401, "not_authenticated")
    return public_user(row)

