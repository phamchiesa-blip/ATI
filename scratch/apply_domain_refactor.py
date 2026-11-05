"""
scratch/apply_domain_refactor.py
--------------------------------
Script ap dung kien truc Domain Entities & DTOs cho Clean Architecture (Buoc 4).
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Wait, ROOT of data_module is os.getcwd()
ROOT = os.path.abspath(".")

def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_text(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

print(f"Applying domain refactor to {ROOT}...")

# 1. Update recommendation/chatbot.py
cb_path = os.path.join(ROOT, "recommendation", "chatbot.py")
cb = read_text(cb_path)

if "from domain.dtos import ChatbotResponseDTO" not in cb:
    cb = cb.replace(
        "from repositories.sqlite_interaction_repo import SqliteInteractionRepository",
        "from repositories.sqlite_interaction_repo import SqliteInteractionRepository\nfrom domain.dtos import ChatbotResponseDTO",
        1,
    )

cb = re.sub(
    r'(\s+)genres = json\.loads\(r\["genres"\] or "\[\]"\)\r?\n\s+cast = json\.loads\(r\["cast"\] or "\[\]"\)',
    r'\1raw_genres = r["genres"]\n\1genres = raw_genres if isinstance(raw_genres, list) else json.loads(raw_genres or "[]")\n\1raw_cast = r["cast"]\n\1cast = raw_cast if isinstance(raw_cast, list) else json.loads(raw_cast or "[]")',
    cb,
    count=1,
)

cb = re.sub(
    r'(\s+)return \{\r?\n\s+"intent": intent\.to_dict\(\),\r?\n\s+"personalized": has_profile,\r?\n\s+"items": items,\r?\n\s+\}',
    r'\1return ChatbotResponseDTO(\n\1    intent=intent.to_dict(),\n\1    personalized=has_profile,\n\1    items=items,\n\1)',
    cb,
    count=1,
)
write_text(cb_path, cb)
print("recommendation/chatbot.py updated!")

# 2. Update ranking_eval/frontend_service.py
fe_path = os.path.join(ROOT, "ranking_eval", "frontend_service.py")
fe = read_text(fe_path)

if "from domain import MovieEntity" not in fe:
    fe = fe.replace(
        "from repositories.sqlite_interaction_repo import SqliteInteractionRepository",
        "from repositories.sqlite_interaction_repo import SqliteInteractionRepository\nfrom domain import MovieEntity, PagedMoviesDTO, OnboardingResultDTO, RecommendationResponseDTO",
        1,
    )

# update _decode_movie
old_decode = """def _decode_movie(row):
    item = dict(row)
    item["genres"] = json.loads(item.get("genres") or "[]")
    item["cast"] = json.loads(item.get("cast") or "[]")
    return item"""

new_decode = """def _decode_movie(row):
    item = dict(row)
    raw_genres = item.get("genres")
    item["genres"] = raw_genres if isinstance(raw_genres, list) else json.loads(raw_genres or "[]")
    raw_cast = item.get("cast")
    item["cast"] = raw_cast if isinstance(raw_cast, list) else json.loads(raw_cast or "[]")
    date = item.get("release_date") or ""
    if date[:4].isdigit():
        item["release_year"] = int(date[:4])
    return MovieEntity.from_dict(item)"""

fe = fe.replace(old_decode, new_decode, 1)

# update onboard_user genre parsing
old_onboard_parse = 'stored_genres = [g.casefold() for g in json.loads(row["genres"] or "[]")]'
new_onboard_parse = 'stored_genres = [g.casefold() for g in (row["genres"] if isinstance(row["genres"], list) else json.loads(row["genres"] or "[]"))]'
fe = fe.replace(old_onboard_parse, new_onboard_parse, 1)

# update onboard_user return
fe = re.sub(
    r'(\s+)return \{\r?\n\s+"ok": True,\r?\n\s+"user_id": user_id,\r?\n\s+"profile_source": source,\r?\n\s+"seed_movie_count": len\(valid_ids\),\r?\n\s+"selected_genres": genres,\r?\n\s+\}',
    r'\1return OnboardingResultDTO(\n\1    ok=True,\n\1    user_id=user_id,\n\1    profile_source=source,\n\1    seed_movie_count=len(valid_ids),\n\1    selected_genres=genres,\n\1)',
    fe,
    count=1,
)

# update recommendations return
fe = re.sub(
    r'(\s+)return \{\r?\n\s+"user_id": user_id,\r?\n\s+"count": len\(items\),\r?\n\s+"items": items,\r?\n\s+\}',
    r'\1return RecommendationResponseDTO(\n\1    user_id=user_id,\n\1    count=len(items),\n\1    items=items,\n\1)',
    fe,
    count=1,
)
write_text(fe_path, fe)
print("ranking_eval/frontend_service.py updated!")

# 3. Update repositories/sqlite_movie_repo.py
sm_path = os.path.join(ROOT, "repositories", "sqlite_movie_repo.py")
sm = read_text(sm_path)

if "from domain import MovieEntity" not in sm:
    sm = sm.replace(
        "from feature_store import (",
        "from domain import MovieEntity, PagedMoviesDTO\nfrom feature_store import (",
        1,
    )

# update get_metadata
old_meta = """    def get_metadata(self, movie_id: int) -> Optional[dict[str, Any]]:
        return _get_movie_metadata(movie_id, db_path=self.db_path)"""
new_meta = """    def get_metadata(self, movie_id: int) -> Optional[MovieEntity]:
        raw = _get_movie_metadata(movie_id, db_path=self.db_path)
        return MovieEntity.from_dict(raw) if raw is not None else None"""
sm = sm.replace(old_meta, new_meta, 1)

# update get_popular_movies return
sm = sm.replace(
    "results.append(item)",
    "results.append(MovieEntity.from_dict(item))",
    1,
)

# update list_movies return
old_list_ret = 'return {"total": total, "page": page, "page_size": page_size, "items": items}'
new_list_ret = 'return PagedMoviesDTO(total=total, page=page, page_size=page_size, items=[MovieEntity.from_dict(m) for m in items])'
sm = sm.replace(old_list_ret, new_list_ret, 1)

# update get_all_movie_rows return
old_all_rows = """            rows = conn.execute(
                'SELECT movie_id, title, overview, genres, director, "cast", '
                'vote_average, vote_count, popularity, release_date '
                'FROM movies ORDER BY movie_id'
            ).fetchall()
            return [dict(r) for r in rows]"""
new_all_rows = """            rows = conn.execute(
                'SELECT movie_id, title, overview, genres, director, "cast", '
                'vote_average, vote_count, popularity, release_date '
                'FROM movies ORDER BY movie_id'
            ).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                raw_g = item.get("genres")
                item["genres"] = raw_g if isinstance(raw_g, list) else json.loads(raw_g or "[]")
                raw_c = item.get("cast")
                item["cast"] = raw_c if isinstance(raw_c, list) else json.loads(raw_c or "[]")
                out.append(MovieEntity.from_dict(item))
            return out"""
sm = sm.replace(old_all_rows, new_all_rows, 1)

# update get_onboarding_candidates
old_onboard_cand = """        with self._connect() as conn:
            rows = conn.execute(
                \"\"\"SELECT movie_id, genres FROM movies
                   WHERE genres IS NOT NULL AND genres != '[]'
                   ORDER BY popularity DESC, vote_count DESC, movie_id ASC\"\"\"
            ).fetchall()
            return [dict(r) for r in rows]"""
new_onboard_cand = """        with self._connect() as conn:
            rows = conn.execute(
                \"\"\"SELECT movie_id, title, overview, genres, director, "cast",
                      vote_average, vote_count, popularity, release_date FROM movies
                   WHERE genres IS NOT NULL AND genres != '[]'
                   ORDER BY popularity DESC, vote_count DESC, movie_id ASC\"\"\"
            ).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                raw_g = item.get("genres")
                item["genres"] = raw_g if isinstance(raw_g, list) else json.loads(raw_g or "[]")
                out.append(MovieEntity.from_dict(item))
            return out"""
sm = sm.replace(old_onboard_cand, new_onboard_cand, 1)
write_text(sm_path, sm)
print("repositories/sqlite_movie_repo.py updated!")

# 4. Update repositories/sqlite_interaction_repo.py
si_path = os.path.join(ROOT, "repositories", "sqlite_interaction_repo.py")
si = read_text(si_path)

if "from domain import InteractionEntity" not in si:
    si = si.replace(
        "from feature_store import DEFAULT_DB_PATH",
        "from domain import InteractionEntity\nfrom feature_store import DEFAULT_DB_PATH",
        1,
    )

old_si_get = """    def get_interactions(self, user_id: str) -> list[dict[str, Any]]:
        return get_user_interactions(user_id, db_path=self.db_path)"""
new_si_get = """    def get_interactions(self, user_id: str) -> list[InteractionEntity]:
        raw = get_user_interactions(user_id, db_path=self.db_path)
        return [InteractionEntity.from_dict(r) for r in raw]"""
si = si.replace(old_si_get, new_si_get, 1)
write_text(si_path, si)
print("repositories/sqlite_interaction_repo.py updated!")

# 5. Update repositories/sqlite_account_repo.py
sa_path = os.path.join(ROOT, "repositories", "sqlite_account_repo.py")
sa = read_text(sa_path)

if "from domain import UserAccountEntity" not in sa:
    sa = sa.replace(
        "from repositories.protocols import AccountRepositoryProtocol",
        "from domain import UserAccountEntity\nfrom repositories.protocols import AccountRepositoryProtocol",
        1,
    )

old_sa_email = """    def get_by_email(self, email: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE email = ?", (email,)).fetchone()
            return dict(row) if row else None"""
new_sa_email = """    def get_by_email(self, email: str) -> Optional[UserAccountEntity]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE email = ?", (email,)).fetchone()
            return UserAccountEntity.from_dict(dict(row)) if row else None"""
sa = sa.replace(old_sa_email, new_sa_email, 1)

old_sa_id = """    def get_by_id(self, user_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None"""
new_sa_id = """    def get_by_id(self, user_id: str) -> Optional[UserAccountEntity]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE id = ?", (user_id,)).fetchone()
            return UserAccountEntity.from_dict(dict(row)) if row else None"""
sa = sa.replace(old_sa_id, new_sa_id, 1)
write_text(sa_path, sa)
print("repositories/sqlite_account_repo.py updated!")

# 6. Update repositories/sqlite_watchlist_repo.py
sw_path = os.path.join(ROOT, "repositories", "sqlite_watchlist_repo.py")
sw = read_text(sw_path)

if "from domain import WatchlistItemEntity" not in sw:
    sw = sw.replace(
        "from repositories.protocols import WatchlistRepositoryProtocol",
        "from domain import WatchlistItemEntity\nfrom repositories.protocols import WatchlistRepositoryProtocol",
        1,
    )

old_sw_get = """    def get_watchlist(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT movie_id, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]"""
new_sw_get = """    def get_watchlist(self, user_id: str) -> list[WatchlistItemEntity]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT movie_id, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
                (user_id,),
            ).fetchall()
            return [WatchlistItemEntity.from_dict(dict(r)) for r in rows]"""
sw = sw.replace(old_sw_get, new_sw_get, 1)
write_text(sw_path, sw)
print("repositories/sqlite_watchlist_repo.py updated!")

# 7. Update server/services/movie_service.py card()
ms_path = os.path.join(ROOT, "server", "services", "movie_service.py")
ms = read_text(ms_path)

if "from domain import MovieCardDTO" not in ms:
    ms = ms.replace(
        "from feature_store import get_all_vectors, get_movie_metadata, get_movie_vector",
        "from domain import MovieCardDTO\nfrom feature_store import get_all_vectors, get_movie_metadata, get_movie_vector",
        1,
    )

old_card = """def card(meta: dict) -> dict:
    \"\"\"Rut gon metadata thanh du lieu card phim cho frontend.\"\"\"
    date = meta.get("release_date") or ""
    return {
        "movie_id": meta["movie_id"],
        "title": meta["title"],
        "overview": meta.get("overview") or "",
        "genres": meta.get("genres", []),
        "director": meta.get("director"),
        "cast": meta.get("cast", []),
        "vote_average": meta.get("vote_average"),
        "popularity": meta.get("popularity"),
        "release_year": int(date[:4]) if date[:4].isdigit() else None,
        "poster_url": poster_url(meta["movie_id"]),
    }"""

new_card = """def card(meta: dict) -> MovieCardDTO:
    \"\"\"Rut gon metadata thanh du lieu card phim cho frontend.\"\"\"
    date = meta.get("release_date") or ""
    return MovieCardDTO(
        movie_id=meta["movie_id"],
        title=meta["title"],
        overview=meta.get("overview") or "",
        genres=meta.get("genres", []),
        director=meta.get("director"),
        cast=meta.get("cast", []),
        vote_average=meta.get("vote_average"),
        popularity=meta.get("popularity"),
        release_year=int(date[:4]) if date[:4].isdigit() else None,
        poster_url=poster_url(meta["movie_id"]),
    )"""
ms = ms.replace(old_card, new_card, 1)
write_text(ms_path, ms)
print("server/services/movie_service.py updated!")

# 8. Update server/services/profile_service.py popular_fallback
ps_path = os.path.join(ROOT, "server", "services", "profile_service.py")
ps = read_text(ps_path)

if "from domain import RecommendationResponseDTO" not in ps:
    ps = ps.replace(
        "from ranking_eval.frontend_service import get_popular_movies, onboard_user, recommendations as ranked_recommendations",
        "from domain import RecommendationResponseDTO\nfrom ranking_eval.frontend_service import get_popular_movies, onboard_user, recommendations as ranked_recommendations",
        1,
    )

old_fallback = """def popular_fallback(user_id: str, k: int) -> dict:
    \"\"\"Goi y fallback dua tren do pho bien khi chua the personalized.\"\"\"
    items = []
    for m in get_popular_movies(db_path=DB, limit=k, exclude_ids=rated_ids(user_id)):
        c = card(m)
        c.update(match_percent=None, reasons=[], neural_used=False, cold_start=True, breakdown=None)
        items.append(c)
    return {"items": items, "personalized": False, "cold_start": True}"""

new_fallback = """def popular_fallback(user_id: str, k: int) -> RecommendationResponseDTO:
    \"\"\"Goi y fallback dua tren do pho bien khi chua the personalized.\"\"\"
    items = []
    for m in get_popular_movies(db_path=DB, limit=k, exclude_ids=rated_ids(user_id)):
        c = card(m)
        c.update(match_percent=None, reasons=[], neural_used=False, cold_start=True, breakdown=None)
        items.append(c)
    return RecommendationResponseDTO(items=items, personalized=False, cold_start=True)"""
ps = ps.replace(old_fallback, new_fallback, 1)
write_text(ps_path, ps)
print("server/services/profile_service.py updated!")

# 9. Update server/routers/auth.py
ra_path = os.path.join(ROOT, "server", "routers", "auth.py")
ra = read_text(ra_path)
if "from domain import DomainModel, OnboardingRequestDTO" not in ra:
    ra = ra.replace(
        "from pydantic import BaseModel",
        "from pydantic import BaseModel\nfrom domain import DomainModel, OnboardingRequestDTO",
        1,
    )
ra = ra.replace("class RegisterBody(BaseModel):", "class RegisterBody(DomainModel):")
ra = ra.replace("class LoginBody(BaseModel):", "class LoginBody(DomainModel):")
ra = ra.replace("class OnboardingBody(BaseModel):", "class OnboardingBody(OnboardingRequestDTO):")
ra = ra.replace("class WatchBody(BaseModel):", "class WatchBody(DomainModel):")
write_text(ra_path, ra)
print("server/routers/auth.py updated!")

# 10. Update server/routers/recommendations.py
rr_path = os.path.join(ROOT, "server", "routers", "recommendations.py")
rr = read_text(rr_path)
if "from domain import FeedbackRequestDTO" not in rr:
    rr = rr.replace(
        "from pydantic import BaseModel",
        "from pydantic import BaseModel\nfrom domain import FeedbackRequestDTO",
        1,
    )
rr = rr.replace("class FeedbackBody(BaseModel):", "class FeedbackBody(FeedbackRequestDTO):")
write_text(rr_path, rr)
print("server/routers/recommendations.py updated!")

# 11. Update server/routers/tonight.py
rt_path = os.path.join(ROOT, "server", "routers", "tonight.py")
rt = read_text(rt_path)
if "from domain import DomainModel" not in rt:
    rt = rt.replace(
        "from pydantic import BaseModel",
        "from pydantic import BaseModel\nfrom domain import DomainModel",
        1,
    )
rt = rt.replace("class TonightChatBody(BaseModel):", "class TonightChatBody(DomainModel):")
write_text(rt_path, rt)
print("server/routers/tonight.py updated!")

print("ALL DOMAIN REFACTORING COMPLETED SUCCESSFULLY!")

