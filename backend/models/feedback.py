"""
feedback.py
------------
Data model for user feedback (Like / Dislike interactions).
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Feedback:
    interaction_id: int
    user_id: str
    movie_id: int
    action: Literal["like", "dislike"]
    created_at: Optional[str] = None


@dataclass
class FeedbackCreate:
    movie_id: int
    action: Literal["like", "dislike"]
