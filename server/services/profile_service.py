import json
import time
from collections import Counter
from typing import Optional

from fastapi import HTTPException

import recommender as _rec
from feature_store import get_movie_metadata, get_movie_vector, get_user_interactions
from domain import RecommendationResponseDTO
from ranking_eval.frontend_service import get_popular_movies, onboard_user, recommendations as ranked_recommendations
from recommender import dislike, like
from repositories.protocols import (
    AccountRepositoryProtocol,
    InteractionRepositoryProtocol,
    WatchlistRepositoryProtocol,
)
from repositories.sqlite_account_repo import SqliteAccountRepository
from repositories.sqlite_interaction_repo import SqliteInteractionRepository
from repositories.sqlite_watchlist_repo import SqliteWatchlistRepository
from server.config import DB
from server.services.movie_service import card

# Repositories mac dinh
_account_repo: AccountRepositoryProtocol = SqliteAccountRepository()
_watchlist_repo: WatchlistRepositoryProtocol = SqliteWatchlistRepository()
_interaction_repo: InteractionRepositoryProtocol = SqliteInteractionRepository()

# Phim yeu thich chon luc onboarding (khong goi y lai chinh chung). Luu trong bo nho.
_seeds: dict[str, set[int]] = {}


def set_profile_repositories(
    account_repo: Optional[AccountRepositoryProtocol] = None,
    watchlist_repo: Optional[WatchlistRepositoryProtocol] = None,
    interaction_repo: Optional[InteractionRepositoryProtocol] = None,
) -> None:
    global _account_repo, _watchlist_repo, _interaction_repo
    if account_repo is not None:
        _account_repo = account_repo
    if watchlist_repo is not None:
        _watchlist_repo = watchlist_repo
    if interaction_repo is not None:
        _interaction_repo = interaction_repo


def rated_ids(user_id: str) -> set[int]:
    """Lay tap ID cac phim ma user da danh gia (like/dislike)."""
    return {h["movie_id"] for h in _interaction_repo.get_interactions(user_id)}


def get_selection(user_id: str) -> Optional[dict]:
    """Lay lua chon the loai va phim yeu thich luc onboarding cua user."""
    row = _account_repo.get_onboarding(user_id)
    if row is None:
        return None
    return {"genres": json.loads(row["genres"]), "favorites": json.loads(row["favorites"])}


def replay_history(user_id: str) -> None:
    """Replay lich su like/dislike de cap nhat lai vector cua profile."""
    prof = _rec._registry.get(user_id)
    if prof is None:
        return
    for ev in _interaction_repo.get_interactions(user_id):
        vec = get_movie_vector(ev["movie_id"], db_path=DB)
        if vec is not None:
            (prof.apply_like if ev["action"] == "like" else prof.apply_dislike)(vec)


def ensure_profile(user_id: str) -> None:
    """Dam bao profile cua nguoi dung da duoc khoi tao trong bo nho."""
    prof = _rec._registry.get(user_id)
    if prof is not None and prof.is_initialized():
        return
    sel = get_selection(user_id)
    if sel is None:
        return
    onboard_user(
        user_id,
        db_path=DB,
        selected_genres=sel["genres"],
        favorite_movie_ids=sel["favorites"],
    )
    replay_history(user_id)
    _seeds[user_id] = set(sel["favorites"])


def popular_fallback(user_id: str, k: int) -> RecommendationResponseDTO:
    """Goi y fallback dua tren do pho bien khi chua the personalized."""
    items = []
    for m in get_popular_movies(db_path=DB, limit=k, exclude_ids=rated_ids(user_id)):
        c = card(m)
        c.update(match_percent=None, reasons=[], neural_used=False, cold_start=True, breakdown=None)
        items.append(c)
    return RecommendationResponseDTO(items=items, personalized=False, cold_start=True)


def breakdown(r: dict) -> Optional[dict]:
    """Phan rã chi tiet diem danh gia da muc tieu."""
    if "rating_score" not in r:
        return None
    return {
        "cosine": round(r["cosine_score"], 3),
        "rating": round(r["rating_score"], 3),
        "popularity": round(r["popularity_score"], 3),
        "newness": round(r["newness_score"], 3),
        "neural": round(r["nn_like_probability"], 3) if r.get("neural_used") else None,
    }


def handle_onboarding(user_id: str, genres: list[str], favorite_movie_ids: list[int]) -> dict:
    _rec._registry._profiles.pop(user_id, None)
    try:
        res = onboard_user(
            user_id,
            db_path=DB,
            selected_genres=genres,
            favorite_movie_ids=favorite_movie_ids,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    favorites = favorite_movie_ids if res["profile_source"] == "favorite_movies" else []
    _account_repo.save_onboarding(user_id, json.dumps(genres), json.dumps(favorites))
    replay_history(user_id)
    _seeds[user_id] = set(favorites)
    return {"ok": True, "seed_count": res["seed_movie_count"]}


def handle_feedback(user_id: str, movie_id: int, action: str) -> dict:
    if action not in ("like", "dislike"):
        raise HTTPException(400, "action phai la 'like' hoac 'dislike'")
    if movie_id in rated_ids(user_id):
        raise HTTPException(409, "already_rated")
    ensure_profile(user_id)
    try:
        (like if action == "like" else dislike)(user_id, movie_id, db_path=DB)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True}


def get_recommendations(user_id: str, k: int = 12, mode: str = "proposed") -> dict:
    ensure_profile(user_id)
    seeds = _seeds.get(user_id, set())
    want = k + len(seeds)
    mode = "baseline" if mode == "baseline" else "proposed"
    try:
        ranked = ranked_recommendations(
            user_id, db_path=DB, limit=want, candidate_k=max(100, want + 20)
        )["items"]
    except RuntimeError:
        return popular_fallback(user_id, k)
    except ValueError as e:
        raise HTTPException(400, str(e))

    cold = bool(ranked) and all(float(r.get("cosine", 0.0)) == 0.0 for r in ranked)
    if mode == "baseline" and not cold:
        try:
            rows_all = [
                {"movie_id": m, "cosine": sc, "final_score": sc}
                for m, sc in _rec.recommend(user_id, k=want, db_path=DB)
            ]
        except RuntimeError:
            return popular_fallback(user_id, k)
    else:
        rows_all = ranked

    rows = [r for r in rows_all if r["movie_id"] not in seeds][:k]

    sel = get_selection(user_id) or {"genres": []}
    liked_genres = Counter(sel["genres"])
    liked = list(seeds) + [
        h["movie_id"] for h in _interaction_repo.get_interactions(user_id) if h["action"] == "like"
    ]
    for mid in liked:
        m = get_movie_metadata(mid, db_path=DB)
        if m:
            liked_genres.update(m["genres"])

    items = []
    for r in rows:
        c = card(get_movie_metadata(r["movie_id"], db_path=DB))
        c["score"] = round(r["final_score"], 4)
        c["cosine"] = round(r["cosine"], 4)
        c["neural_used"] = bool(r.get("neural_used"))
        c["cold_start"] = cold
        c["match_percent"] = None if cold else round(max(0.0, min(1.0, r["final_score"])) * 100)
        c["reasons"] = (
            [] if cold else [g for g, _ in liked_genres.most_common() if g in c["genres"]][:3]
        )
        c["breakdown"] = breakdown(r)
        items.append(c)

    return {"items": items, "personalized": not cold, "cold_start": cold, "mode": mode}


def get_user_history(user_id: str) -> dict:
    out = []
    for h in _interaction_repo.get_interactions(user_id):
        meta = get_movie_metadata(h["movie_id"], db_path=DB)
        if meta:
            out.append({**card(meta), "action": h["action"], "created_at": h["created_at"]})
    return {"items": out}


def reset_user_profile(user_id: str) -> dict:
    _rec._registry._profiles.pop(user_id, None)
    _seeds.pop(user_id, None)
    _interaction_repo.delete_interactions(user_id)
    _account_repo.reset_onboarding(user_id)
    return {"ok": True}


def get_watchlist(user_id: str) -> dict:
    rows = _watchlist_repo.get_watchlist(user_id)
    items = []
    for r in rows:
        meta = get_movie_metadata(r["movie_id"], db_path=DB)
        if meta:
            items.append({**card(meta), "added_at": r["added_at"]})
    return {"items": items}


def add_watchlist(user_id: str, movie_id: int) -> dict:
    if get_movie_metadata(movie_id, db_path=DB) is None:
        raise HTTPException(404, "Không tìm thấy phim")
    _watchlist_repo.add_to_watchlist(user_id, movie_id, time.time())
    return {"ok": True}


def remove_watchlist(user_id: str, movie_id: int) -> dict:
    _watchlist_repo.remove_from_watchlist(user_id, movie_id)
    return {"ok": True}
