"""
backend/services/recommendation_service.py
------------------------------------------
Use cases cho Ho so nguoi dung (Onboarding, Like/Dislike, Lich su, Watchlist, Goi y ca nhan hoa,
va 'Hom nay xem gi?' / Conversational Recommender).
"""

import json
import os
import time
from collections import Counter
from typing import List, Optional

from fastapi import HTTPException

from backend.core.config import DB
from backend.core.database import accounts_db, movies_db
from backend.repositories.movie_repository import (
    get_poster_url,
    load_extra_metadata,
    to_movie_card,
)
from chatbot import GENRE_VI_LABELS, QUICK_SUGGESTIONS, chat_recommend, get_feature_space
from feature_store import get_movie_metadata, get_movie_vector, get_user_interactions
from ranking_eval.frontend_service import (
    get_popular_movies,
    onboard_user,
    recommendations as ranked_recommendations,
)
import recommender as _rec
from recommender import dislike, like

# Phim yeu thich chon luc onboarding (khong goi y lai chinh chung). Luu trong bo nho.
_seeds: dict[str, set[int]] = {}

MOODS = [
    {
        "id": "happy",
        "label": "Vui vẻ, nhẹ nhàng",
        "genres": ["Comedy", "Animation", "Family"],
        "avoid": ["Horror", "War", "Crime"],
    },
    {
        "id": "thrill",
        "label": "Hồi hộp, căng thẳng",
        "genres": ["Thriller", "Mystery", "Crime"],
        "avoid": ["Family", "Animation"],
    },
    {
        "id": "touching",
        "label": "Cảm động, sâu lắng",
        "genres": ["Drama", "Romance"],
        "avoid": ["Horror"],
    },
    {
        "id": "excited",
        "label": "Phấn khích, mãn nhãn",
        "genres": ["Action", "Adventure", "Science Fiction"],
        "avoid": [],
    },
    {
        "id": "scary",
        "label": "Rùng rợn",
        "genres": ["Horror"],
        "avoid": ["Comedy", "Family", "Animation"],
    },
    {
        "id": "dreamy",
        "label": "Mơ mộng, kỳ ảo",
        "genres": ["Fantasy", "Science Fiction", "Animation"],
        "avoid": ["Horror", "War"],
    },
    {"id": "romantic", "label": "Lãng mạn", "genres": ["Romance"], "avoid": ["Horror", "War"]},
    {
        "id": "think",
        "label": "Suy ngẫm",
        "genres": ["Drama", "History", "Documentary", "Mystery"],
        "avoid": ["Comedy", "Family"],
    },
]

TIMES = [
    {"id": "short", "label": "Dưới 100 phút", "max": 100},
    {"id": "medium", "label": "Khoảng 2 giờ", "max": 130},
    {"id": "any", "label": "Không giới hạn", "max": None},
]


def get_rated_ids(user_id: str) -> set[int]:
    return {h["movie_id"] for h in get_user_interactions(user_id, db_path=DB)}


def get_onboarding_selection(user_id: str) -> Optional[dict]:
    with accounts_db() as c:
        row = c.execute("SELECT * FROM onboarding WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    return {"genres": json.loads(row["genres"]), "favorites": json.loads(row["favorites"])}


def replay_user_history(user_id: str) -> None:
    prof = _rec._registry.get(user_id)
    if prof is None:
        return
    for ev in get_user_interactions(user_id, db_path=DB):
        vec = get_movie_vector(ev["movie_id"], db_path=DB)
        if vec is not None:
            (prof.apply_like if ev["action"] == "like" else prof.apply_dislike)(vec)


def ensure_user_profile(user_id: str) -> None:
    """Khoi phuc profile trong bo nho tu lua chon onboarding + lich su Like/Dislike."""
    prof = _rec._registry.get(user_id)
    if prof is not None and prof.is_initialized():
        return
    sel = get_onboarding_selection(user_id)
    if sel is None:
        return
    onboard_user(
        user_id,
        db_path=DB,
        selected_genres=sel["genres"],
        favorite_movie_ids=sel["favorites"],
    )
    replay_user_history(user_id)
    _seeds[user_id] = set(sel["favorites"])


def save_onboarding(user_id: str, genres: List[str], favorite_movie_ids: List[int]) -> dict:
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
    with accounts_db() as c:
        c.execute(
            "INSERT OR REPLACE INTO onboarding VALUES (?, ?, ?)",
            (user_id, json.dumps(genres), json.dumps(favorites)),
        )
        c.execute("UPDATE accounts SET onboarded = 1 WHERE id = ?", (user_id,))
    replay_user_history(user_id)
    _seeds[user_id] = set(favorites)
    return {"ok": True, "seed_count": res["seed_movie_count"]}


def record_feedback(user_id: str, movie_id: int, action: str) -> dict:
    if action not in ("like", "dislike"):
        raise HTTPException(400, "action phai la 'like' hoac 'dislike'")
    if movie_id in get_rated_ids(user_id):
        raise HTTPException(409, "already_rated")
    ensure_user_profile(user_id)
    try:
        (like if action == "like" else dislike)(user_id, movie_id, db_path=DB)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True}


def delete_feedback(user_id: str, movie_id: int) -> dict:
    with movies_db() as c:
        n = c.execute(
            "DELETE FROM user_interaction_history WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id),
        ).rowcount
    if not n:
        raise HTTPException(404, "not_rated")
    _rec._registry._profiles.pop(user_id, None)
    ensure_user_profile(user_id)
    return {"ok": True}


def _popular_fallback(user_id: str, k: int) -> dict:
    items = []
    for m in get_popular_movies(db_path=DB, limit=k, exclude_ids=get_rated_ids(user_id)):
        card = to_movie_card(m)
        card.update(
            match_percent=None,
            reasons=[],
            neural_used=False,
            cold_start=True,
            breakdown=None,
        )
        items.append(card)
    return {"items": items, "personalized": False, "cold_start": True}


def _score_breakdown(r: dict) -> Optional[dict]:
    if "rating_score" not in r:
        return None
    return {
        "cosine": round(r["cosine_score"], 3),
        "rating": round(r["rating_score"], 3),
        "popularity": round(r["popularity_score"], 3),
        "newness": round(r["newness_score"], 3),
        "neural": round(r["nn_like_probability"], 3) if r.get("neural_used") else None,
    }


def get_user_recommendations(user_id: str, k: int = 12, mode: str = "proposed") -> dict:
    ensure_user_profile(user_id)
    seeds = _seeds.get(user_id, set())
    want = k + len(seeds)
    mode = "baseline" if mode == "baseline" else "proposed"
    try:
        ranked = ranked_recommendations(
            user_id, db_path=DB, limit=want, candidate_k=max(100, want + 20)
        )["items"]
    except RuntimeError:
        return _popular_fallback(user_id, k)
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
            return _popular_fallback(user_id, k)
    else:
        rows_all = ranked
    rows = [r for r in rows_all if r["movie_id"] not in seeds][:k]

    sel = get_onboarding_selection(user_id) or {"genres": []}
    liked_genres = Counter(sel["genres"])
    liked = list(seeds) + [
        h["movie_id"] for h in get_user_interactions(user_id, db_path=DB) if h["action"] == "like"
    ]
    for mid in liked:
        m = get_movie_metadata(mid, db_path=DB)
        if m:
            liked_genres.update(m["genres"])

    items = []
    for r in rows:
        card = to_movie_card(get_movie_metadata(r["movie_id"], db_path=DB))
        card["score"] = round(r["final_score"], 4)
        card["cosine"] = round(r["cosine"], 4)
        card["neural_used"] = bool(r.get("neural_used"))
        card["cold_start"] = cold
        card["match_percent"] = (
            None if cold else round(max(0.0, min(1.0, r["final_score"])) * 100)
        )
        card["reasons"] = (
            []
            if cold
            else [g for g, _ in liked_genres.most_common() if g in card["genres"]][:3]
        )
        card["breakdown"] = _score_breakdown(r)
        items.append(card)
    return {"items": items, "personalized": not cold, "cold_start": cold, "mode": mode}


def get_interaction_history(user_id: str) -> dict:
    out = []
    for h in get_user_interactions(user_id, db_path=DB):
        meta = get_movie_metadata(h["movie_id"], db_path=DB)
        if meta:
            out.append({**to_movie_card(meta), "action": h["action"], "created_at": h["created_at"]})
    return {"items": out}


def reset_user_profile(user_id: str) -> dict:
    _rec._registry._profiles.pop(user_id, None)
    _seeds.pop(user_id, None)
    with movies_db() as c:
        c.execute("DELETE FROM user_interaction_history WHERE user_id = ?", (user_id,))
    with accounts_db() as c:
        c.execute("DELETE FROM onboarding WHERE user_id = ?", (user_id,))
        c.execute("UPDATE accounts SET onboarded = 0 WHERE id = ?", (user_id,))
    return {"ok": True}


def list_watchlist(user_id: str) -> dict:
    with accounts_db() as c:
        rows = c.execute(
            "SELECT movie_id, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,),
        ).fetchall()
    items = []
    for r in rows:
        meta = get_movie_metadata(r["movie_id"], db_path=DB)
        if meta:
            items.append({**to_movie_card(meta), "added_at": r["added_at"]})
    return {"items": items}


def add_to_watchlist(user_id: str, movie_id: int) -> dict:
    if get_movie_metadata(movie_id, db_path=DB) is None:
        raise HTTPException(404, "Không tìm thấy phim")
    with accounts_db() as c:
        c.execute(
            "INSERT OR IGNORE INTO watchlist VALUES (?, ?, ?)",
            (user_id, movie_id, time.time()),
        )
    return {"ok": True}


def remove_from_watchlist(user_id: str, movie_id: int) -> dict:
    with accounts_db() as c:
        c.execute("DELETE FROM watchlist WHERE user_id = ? AND movie_id = ?", (user_id, movie_id))
    return {"ok": True}


def get_tonight_options() -> dict:
    return {
        "moods": [{k: m[k] for k in ("id", "label", "genres")} for m in MOODS],
        "times": [{"id": t["id"], "label": t["label"]} for t in TIMES],
        "quick_suggestions": QUICK_SUGGESTIONS,
        "genre_labels": [
            {"id": g, "label": GENRE_VI_LABELS.get(g, g)}
            for g in get_feature_space(DB).genre_labels
        ],
        "llm_available": bool(
            os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("OPENAI_API_KEY", "").strip()
        ),
    }


def recommend_tonight_chat(
    user_id: str,
    message: str,
    previous_intent: Optional[dict],
    intent_override: Optional[dict],
    exclude: List[int],
    top_n: int,
    use_llm: bool,
) -> dict:
    if not message.strip() and not intent_override and not previous_intent:
        raise HTTPException(400, "Hãy nhập yêu cầu hoặc chọn một gợi ý nhanh")
    ensure_user_profile(user_id)
    extras = load_extra_metadata()
    runtimes = {mid: info.get("runtime") for mid, info in extras.items()} if extras else None
    seeds = _seeds.get(user_id, set())
    exclude_set = set(exclude) | seeds

    try:
        res = chat_recommend(
            user_id,
            message,
            db_path=DB,
            previous_intent=previous_intent,
            intent_override=intent_override,
            exclude_ids=exclude_set,
            runtimes=runtimes,
            top_n=min(max(top_n, 1), 24),
            use_llm=use_llm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    for item in res["items"]:
        item["poster_url"] = get_poster_url(item["movie_id"])
    res["runtime_filter_applied"] = bool(extras) and bool(res["intent"].get("max_runtime"))
    return res


def recommend_tonight_by_mood(user_id: str, mood_id: str, time_id: str, exclude: List[int]) -> dict:
    mood = next((m for m in MOODS if m["id"] == mood_id), None)
    if mood is None:
        raise HTTPException(400, "Tâm trạng không hợp lệ")
    limit = next((t["max"] for t in TIMES if t["id"] == time_id), None)
    ensure_user_profile(user_id)
    try:
        ranked = ranked_recommendations(user_id, db_path=DB, limit=500, candidate_k=500)["items"]
    except (RuntimeError, ValueError):
        ranked = []
    personalized = bool(ranked) and any(float(r.get("cosine", 0.0)) > 0.0 for r in ranked)
    own = {r["movie_id"] for r in ranked} if personalized else set()
    with movies_db() as c:
        filler = [
            r["movie_id"]
            for r in c.execute("SELECT movie_id FROM movies ORDER BY popularity DESC")
        ]
    ranked = [{"movie_id": r["movie_id"]} for r in ranked] + [{"movie_id": m} for m in filler]

    extras = load_extra_metadata()
    skip = set(exclude) | get_rated_ids(user_id)
    seen = set()
    want, avoid = set(mood["genres"]), set(mood["avoid"])
    items = []
    for r in ranked:
        mid = r["movie_id"]
        if mid in seen:
            continue
        seen.add(mid)
        meta = get_movie_metadata(mid, db_path=DB)
        if mid in skip or meta is None:
            continue
        genres = set(meta["genres"])
        if not genres & want or genres & avoid:
            continue
        if (meta.get("vote_count") or 0) < 200 or (meta.get("vote_average") or 0) < 6.2:
            continue
        runtime = extras.get(mid, {}).get("runtime")
        if limit and runtime and runtime > limit:
            continue
        card = to_movie_card(meta)
        card["runtime"] = runtime
        card["why"] = " · ".join(
            filter(
                None,
                [
                    f"Hợp tâm trạng “{mood['label']}”",
                    f"{runtime} phút" if runtime else None,
                    "hợp gu của bạn" if mid in own else "được nhiều người yêu thích",
                ],
            )
        )
        items.append(card)
        if len(items) >= 10:
            break
    return {
        "items": items,
        "personalized": personalized,
        "mood": mood["label"],
        "runtime_filter_applied": bool(extras) and limit is not None,
    }

