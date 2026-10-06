"""
user.py
--------
Pydantic-style data model for a User.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    user_id: str
    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    created_at: Optional[str] = None


@dataclass
class UserCreate:
    username: str
    email: str
    password: str


@dataclass
class UserLogin:
    email: str
    password: str
