"""Independent reranking helpers for candidates produced by another module.

Candidate dictionaries need ``movie_id`` and ``cosine``. Rating, popularity,
and release year are optional; absent values receive a neutral normalized
score. Scores are normalized within the provided candidate list so inputs
from different scales can be combined simply.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable


@dataclass(frozen=True)
class RankingWeights:
    cosine: float = 0.60
    rating: float = 0.20
    popularity: float = 0.10
    newness: float = 0.10

    def __post_init__(self) -> None:
        values = (self.cosine, self.rating, self.popularity, self.newness)
        if any(value < 0 for value in values) or sum(values) <= 0:
            raise ValueError("Ranking weights must be non-negative with a positive sum.")


def _number(value: Any, default: float | None = None) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if result == result else default


def _minmax(values: list[float | None], *, missing: float = 0.5) -> list[float]:
    present = [value for value in values if value is not None]
    if not present:
        return [missing] * len(values)
    low, high = min(present), max(present)
    if high == low:
        return [missing if value is None else 0.5 for value in values]
    return [missing if value is None else (value - low) / (high - low) for value in values]


def _year(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value)[:4])
    except (TypeError, ValueError):
        return None


def rank_candidates(
    candidates: Iterable[dict[str, Any]],
    weights: RankingWeights = RankingWeights(),
    *,
    current_year: int | None = None,
) -> list[dict[str, Any]]:
    """Return copied candidates sorted by weighted final score descending.

    Metadata keys accepted: ``vote_average`` or ``rating``, ``popularity``,
    and ``release_year`` or ``release_date``. The return items include the
    original fields plus ``ranking_score`` and normalized component scores.
    """
    rows = [dict(row) for row in candidates]
    if not rows:
        return []
    year_now = current_year or date.today().year
    cosine = _minmax([_number(r.get("cosine")) for r in rows])
    rating = _minmax([_number(r.get("vote_average", r.get("rating"))) for r in rows])
    popularity = _minmax([_number(r.get("popularity")) for r in rows])
    raw_years = [_year(r.get("release_year", r.get("release_date"))) for r in rows]
    newness = [0.5 if y is None else min(1.0, max(0.0, (y - 1900) / max(1, year_now - 1900))) for y in raw_years]

    total_weight = weights.cosine + weights.rating + weights.popularity + weights.newness
    for i, row in enumerate(rows):
        components = {
            "cosine_score": cosine[i],
            "rating_score": rating[i],
            "popularity_score": popularity[i],
            "newness_score": newness[i],
        }
        row.update(components)
        row["ranking_score"] = sum(
            components[key] * weight
            for key, weight in (
                ("cosine_score", weights.cosine),
                ("rating_score", weights.rating),
                ("popularity_score", weights.popularity),
                ("newness_score", weights.newness),
            )
        ) / total_weight
    return sorted(rows, key=lambda row: row["ranking_score"], reverse=True)


def baseline_rank(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Simple baseline: preserve the ordering by cosine similarity alone."""
    return sorted(
        (dict(row) for row in candidates),
        key=lambda row: _number(row.get("cosine"), default=float("-inf")),
        reverse=True,
    )
