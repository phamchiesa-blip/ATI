import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from domain import DomainModel

from chatbot import (
    GENRE_VI_LABELS,
    QUICK_SUGGESTIONS,
    chat_recommend,
    get_feature_space,
)
from feature_store import get_movie_metadata
from ranking_eval.frontend_service import recommendations as ranked_recommendations
from server.config import DB, MOODS, TIMES
from server.database import db_conn
from server.dependencies import current_user
from server.services.movie_service import card, load_extra, poster_url
from server.services.profile_service import _seeds, ensure_profile, rated_ids

router = APIRouter(tags=["Tonight"])


@router.get("/api/tonight/options")
def tonight_options():
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


class TonightChatBody(DomainModel):
    message: str = ""
    previous_intent: Optional[dict] = None
    intent_override: Optional[dict] = None
    exclude: List[int] = []
    top_n: int = 10
    use_llm: bool = True


@router.post("/api/tonight/chat")
def tonight_chat(body: TonightChatBody, user: dict = Depends(current_user)):
    """Endpoint Chat Bot cho muc 'Hom nay xem gi?':
    Hieu yeu cau tu nhien -> Dung Query Vector 324 chieu -> Loc phim tranh ->
    Tinh Cosine & tron voi User Profile + Ranking -> Tra ve danh sach phim + ly do."""
    if not body.message.strip() and not body.intent_override and not body.previous_intent:
        raise HTTPException(400, "Hãy nhập yêu cầu hoặc chọn một gợi ý nhanh")
    uid = user["id"]
    ensure_profile(uid)
    extras = load_extra()
    runtimes = {mid: info.get("runtime") for mid, info in extras.items()} if extras else None
    seeds = _seeds.get(uid, set())
    exclude_set = set(body.exclude) | seeds

    try:
        res = chat_recommend(
            uid,
            body.message,
            db_path=DB,
            previous_intent=body.previous_intent,
            intent_override=body.intent_override,
            exclude_ids=exclude_set,
            runtimes=runtimes,
            top_n=min(max(body.top_n, 1), 24),
            use_llm=body.use_llm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    for item in res["items"]:
        item["poster_url"] = poster_url(item["movie_id"])
    res["runtime_filter_applied"] = bool(extras) and bool(res["intent"].get("max_runtime"))
    return res


class TonightBody(BaseModel):
    mood: str
    time: str = "any"
    exclude: List[int] = []


@router.post("/api/tonight")
def tonight(body: TonightBody, user: dict = Depends(current_user)):
    mood = next((m for m in MOODS if m["id"] == body.mood), None)
    if mood is None:
        raise HTTPException(400, "Tâm trạng không hợp lệ")
    limit = next((t["max"] for t in TIMES if t["id"] == body.time), None)
    uid = user["id"]
    ensure_profile(uid)
    try:
        ranked = ranked_recommendations(uid, db_path=DB, limit=500, candidate_k=500)["items"]
    except (RuntimeError, ValueError):
        ranked = []
    personalized = bool(ranked) and any(float(r.get("cosine", 0.0)) > 0.0 for r in ranked)
    own = {r["movie_id"] for r in ranked} if personalized else set()

    with db_conn() as c:
        filler = [r["movie_id"] for r in c.execute("SELECT movie_id FROM movies ORDER BY popularity DESC")]
    ranked = [{"movie_id": r["movie_id"]} for r in ranked] + [{"movie_id": m} for m in filler]

    extras = load_extra()
    skip = set(body.exclude) | rated_ids(uid)
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
        c = card(meta)
        c["runtime"] = runtime
        c["why"] = " · ".join(
            filter(
                None,
                [
                    f"Hợp tâm trạng “{mood['label']}”",
                    f"{runtime} phút" if runtime else None,
                    "hợp gu của bạn" if mid in own else "được nhiều người yêu thích",
                ],
            )
        )
        items.append(c)
        if len(items) >= 10:
            break
    return {
        "items": items,
        "personalized": personalized,
        "mood": mood["label"],
        "runtime_filter_applied": bool(extras) and limit is not None,
    }

