"""
test_chatbot.py
---------------
Bo kiem thu cho module Chat Bot "Hom nay xem gi?" (recommendation/chatbot.py):
  - Danh gia dinh tinh tren tap mau nho 20 cau truy van da dang (tieng Viet, tieng Anh,
    tam trang, the loai muon/tranh, "giong phim X", thoi ky/nam, dao dien/dien vien,
    tu khoa TF-IDF/SVD) o ca hai che do:
      1) Local mode (use_llm=False): Tu dien + Khop ten phim + TF-IDF/SVD 324 chieu
      2) LLM fallback mode (use_llm=True): Co key thi goi LLM, khong co key thi tu dong roi ve Local
  - Kiem tra hoi thoai nhieu luot (multi-turn refinement: "cho minh cai nhe hon nua", "tranh kinh di"...).
  - Kiem tra tron Query Vector 324 chieu voi User Profile va Multi-Objective Ranking.
  - Ghi ro: Day la danh gia dinh tinh tren tap mau nho (n = 20 cau mau).
"""

from __future__ import annotations

import os
import sys

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_REC_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_REC_DIR, ".."))
_DATA_SRC = os.path.join(_ROOT, "data_module", "src")
for _p in (_ROOT, _DATA_SRC, _REC_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from feature_store import DEFAULT_DB_PATH, check_db_exists
from chatbot import (
    ChatIntent,
    build_query_vector,
    chat_recommend,
    get_feature_space,
    parse_user_query,
)
import recommender as _rec

DB_PATH = os.environ.get("ATI_TEST_DB_PATH", DEFAULT_DB_PATH)

# 20 cau mau kiem thu dinh tinh (Qualitative Evaluation, Small Sample n=20)
SAMPLE_20_QUERIES = [
    {
        "id": 1,
        "query": "Hôm nay mình muốn xem phim hài nhẹ nhàng, thư giãn cuối tuần, tránh kinh dị",
        "expect_want_any": {"Comedy", "Romance", "Family", "Animation"},
        "expect_avoid_any": {"Horror"},
    },
    {
        "id": 2,
        "query": "Gợi ý phim hành động hồi hộp căng thẳng, không thích tình cảm lãng mạn",
        "expect_want_any": {"Action", "Thriller"},
        "expect_avoid_any": {"Romance"},
    },
    {
        "id": 3,
        "query": "Tìm phim khoa học viễn tưởng xoắn não giống Inception",
        "expect_want_any": {"Science Fiction", "Mystery", "Thriller", "Action"},
        "expect_similar_title": "Inception",
    },
    {
        "id": 4,
        "query": "Phim hoạt hình gia đình vui nhộn giống Finding Nemo cho trẻ em",
        "expect_want_any": {"Animation", "Family", "Comedy"},
        "expect_similar_title": "Finding Nemo",
    },
    {
        "id": 5,
        "query": "Đang buồn muốn xem phim tâm lý tình cảm sâu lắng, cảm động",
        "expect_want_any": {"Drama", "Romance"},
        "expect_avoid_any": {"Horror"},
    },
    {
        "id": 6,
        "query": "Phim kinh dị rùng rợn ám ảnh về ma quỷ hoặc xác sống",
        "expect_want_any": {"Horror", "Thriller"},
    },
    {
        "id": 7,
        "query": "Phim trinh thám phá án bí ẩn có plot twist bất ngờ, tránh hoạt hình",
        "expect_want_any": {"Mystery", "Crime", "Thriller"},
        "expect_avoid_any": {"Animation"},
    },
    {
        "id": 8,
        "query": "Phim phiêu lưu kỳ ảo phép thuật giống The Lord of the Rings",
        "expect_want_any": {"Fantasy", "Adventure"},
        "expect_similar_title": "The Lord of the Rings",
    },
    {
        "id": 9,
        "query": "Phim hành động mãn nhãn thập niên 2010s, tránh phim chiến tranh",
        "expect_want_any": {"Action", "Adventure", "Science Fiction"},
        "expect_avoid_any": {"War"},
        "expect_year_from": 2010,
    },
    {
        "id": 10,
        "query": "Phim lãng mạn thập niên 90 nhẹ nhàng",
        "expect_want_any": {"Romance", "Comedy"},
        "expect_year_range": (1990, 1999),
    },
    {
        "id": 11,
        "query": "Phim khoa học viễn tưởng về du hành vũ trụ giống Interstellar",
        "expect_want_any": {"Science Fiction", "Adventure", "Drama"},
        "expect_similar_title": "Interstellar",
    },
    {
        "id": 12,
        "query": "Phim hài vui vẻ dưới 100 phút để xem nhanh giờ nghỉ trưa",
        "expect_want_any": {"Comedy", "Animation", "Family"},
        "expect_max_runtime": 100,
    },
    {
        "id": 13,
        "query": "Phim tội phạm mafia hình sự gay cấn của đạo diễn Martin Scorsese",
        "expect_want_any": {"Crime", "Drama", "Thriller"},
        "expect_director": "Martin Scorsese",
    },
    {
        "id": 14,
        "query": "Phim hành động bom tấn có diễn viên Bruce Willis",
        "expect_want_any": {"Action"},
        "expect_actor": "Bruce Willis",
    },
    {
        "id": 15,
        "query": "Phim lịch sử chiến tranh hào hùng từ năm 2000 đến 2015, tránh hài",
        "expect_want_any": {"History", "War", "Drama"},
        "expect_avoid_any": {"Comedy"},
        "expect_year_range": (2000, 2015),
    },
    {
        "id": 16,
        "query": "I want a thrilling sci-fi movie about artificial intelligence and time travel, no horror",
        "expect_want_any": {"Science Fiction", "Thriller"},
        "expect_avoid_any": {"Horror"},
    },
    {
        "id": 17,
        "query": "Phim tài liệu truyền cảm hứng hoặc tiểu sử có thật, tránh bạo lực",
        "expect_want_any": {"Documentary", "Drama", "History"},
        "expect_avoid_any": {"Horror"},
    },
    {
        "id": 18,
        "query": "Phim viễn tây cao bồi kinh điển trước năm 2000",
        "expect_want_any": {"Western"},
        "expect_year_to": 2000,
    },
    {
        "id": 19,
        "query": "Phim âm nhạc học đường tuổi trẻ sôi động, vui tươi",
        "expect_want_any": {"Music", "Comedy", "Family"},
    },
    {
        "id": 20,
        "query": "Phim siêu anh hùng kiểu như The Dark Knight nhưng từ năm 2010",
        "expect_want_any": {"Action", "Crime", "Drama", "Science Fiction"},
        "expect_similar_title": "The Dark Knight",
        "expect_year_from": 2010,
    },
]


def evaluate_20_queries(use_llm: bool = False) -> dict:
    check_db_exists(DB_PATH)
    space = get_feature_space(DB_PATH)
    uid = "test_chatbot_eval_user"
    _rec._registry._profiles.pop(uid, None)

    intent_matched = 0
    rec_genre_matched = 0
    avoid_violated = 0
    rows_report = []

    for case in SAMPLE_20_QUERIES:
        res = chat_recommend(
            uid,
            case["query"],
            db_path=DB_PATH,
            top_n=5,
            use_llm=use_llm,
        )
        intent = res["intent"]
        items = res["items"]
        assert len(items) > 0, f"Query #{case['id']} returned 0 movies!"

        # 1. Kiem tra Intent co khop the loai mong doi khong
        wanted_set = set(intent["wanted_genres"])
        avoid_set = set(intent["avoid_genres"])
        expect_want = case.get("expect_want_any", set())
        ok_intent = bool(wanted_set & expect_want) if expect_want else True

        if "expect_avoid_any" in case:
            ok_intent = ok_intent and bool(avoid_set & case["expect_avoid_any"])
        if "expect_similar_title" in case:
            sim_titles = " ".join(m["title"] for m in intent["similar_movies"])
            ok_intent = ok_intent and (case["expect_similar_title"].lower() in sim_titles.lower())
        if "expect_year_from" in case:
            ok_intent = ok_intent and (intent["year_from"] == case["expect_year_from"])
        if "expect_year_to" in case:
            ok_intent = ok_intent and (intent["year_to"] == case["expect_year_to"])
        if "expect_year_range" in case:
            ok_intent = ok_intent and (
                (intent["year_from"], intent["year_to"]) == case["expect_year_range"]
            )
        if "expect_max_runtime" in case:
            ok_intent = ok_intent and (intent["max_runtime"] == case["expect_max_runtime"])
        if "expect_director" in case:
            ok_intent = ok_intent and (intent["director"] == case["expect_director"])
        if "expect_actor" in case:
            ok_intent = ok_intent and (intent["actor"] == case["expect_actor"])

        if ok_intent:
            intent_matched += 1

        # 2. Kiem tra Top-5 phim goi y: co khop the loai mong doi va KHONG vi pham the loai bi tranh
        top_genres = {g for m in items for g in m["genres"]}
        ok_rec = bool(top_genres & expect_want) if expect_want else True
        if ok_rec:
            rec_genre_matched += 1

        violated = False
        if avoid_set:
            for m in items:
                if set(m["genres"]) & avoid_set:
                    violated = True
                    break
        if violated:
            avoid_violated += 1

        rows_report.append({
            "id": case["id"],
            "query": case["query"],
            "summary_line": intent["summary_line"],
            "parser_source": intent["parser_source"],
            "top1_title": items[0]["title"],
            "top1_genres": items[0]["genres"],
            "top1_why": items[0]["why"],
            "ok_intent": ok_intent,
            "ok_rec": ok_rec,
            "avoid_violated": violated,
        })

    return {
        "total": len(SAMPLE_20_QUERIES),
        "intent_matched": intent_matched,
        "rec_genre_matched": rec_genre_matched,
        "avoid_violated": avoid_violated,
        "rows": rows_report,
    }


def test_multi_turn_and_profile_blending():
    print("=== Test Multi-Turn Refinement & 324-D Query Vector ===")
    space = get_feature_space(DB_PATH)
    uid = "test_chatbot_multiturn_user"
    _rec._registry._profiles.pop(uid, None)

    # Luot 1: "Phim khoa hoc vien tuong hoi hop giong Inception"
    r1 = chat_recommend(
        uid,
        "Phim khoa học viễn tưởng hồi hộp giống Inception",
        db_path=DB_PATH,
        top_n=5,
        use_llm=False,
    )
    i1 = r1["intent"]
    assert "Science Fiction" in i1["wanted_genres"]
    assert any("Inception" in m["title"] for m in i1["similar_movies"])
    # Khong goi y lai chinh phim Inception
    assert all(m["title"] != "Inception" for m in r1["items"])
    print(f"  Turn 1 Summary: {i1['summary_line']}")
    print(f"  Turn 1 Top-1:   {r1['items'][0]['title']} ({r1['items'][0]['why']})")

    # Luot 2: "Cho minh cai nhe hon nua, tranh kinh di"
    r2 = chat_recommend(
        uid,
        "Cho mình cái nhẹ hơn nữa, tránh kinh dị",
        db_path=DB_PATH,
        previous_intent=i1,
        top_n=5,
        use_llm=False,
    )
    i2 = r2["intent"]
    assert i2["is_followup"] is True, "Turn 2 must be detected as a follow-up refinement"
    assert "Comedy" in i2["wanted_genres"] or "Family" in i2["wanted_genres"]
    assert "Horror" in i2["avoid_genres"]
    for m in r2["items"]:
        assert "Horror" not in m["genres"], f"Horror movie leaked into Turn 2: {m['title']}"
    print(f"  Turn 2 Summary: {i2['summary_line']}")
    print(f"  Turn 2 Top-1:   {r2['items'][0]['title']} ({r2['items'][0]['why']})")

    # Kiem tra Query Vector 324 chieu
    q_vec = build_query_vector(parse_user_query("Phim hài nhẹ nhàng", db_path=DB_PATH, use_llm=False), space)
    assert q_vec.shape == (324,), f"Expected 324-d query vector, got {q_vec.shape}"
    print(f"  Query Vector shape OK: {q_vec.shape}, L2 norm={float((q_vec**2).sum()**0.5):.3f}\n")


def test_keyword_queries():
    print("=== Test TMDB Keyword Search (marvel, breaking the fourth wall) ===")
    uid = "test_kw_user"
    # 1. Marvel query must recommend Deadpool in top 3
    res_m = chat_recommend(uid, "marvel", db_path=DB_PATH, use_llm=False)
    titles_m = [m["title"] for m in res_m["items"]]
    assert "Deadpool" in titles_m[:3], f"Expected Deadpool in top 3 for 'marvel', got: {titles_m[:3]}"
    assert res_m["intent"]["matched_keywords"], "Expected matched_keywords for 'marvel'"
    print(f"  OK marvel: Top-1={titles_m[0]}, matched_keywords={res_m['intent']['matched_keywords']}")

    # 2. Breaking the fourth wall must recommend Deadpool
    res_w = chat_recommend(uid, "breaking the fourth wall", db_path=DB_PATH, use_llm=False)
    titles_w = [m["title"] for m in res_w["items"]]
    assert "Deadpool" in titles_w, f"Expected Deadpool in recommendations for 'breaking the fourth wall'"
    print(f"  OK breaking the fourth wall: Top-1={titles_w[0]}")
    print("  Keyword search test passed successfully!\n")


def test_freeform_plot_and_content_queries():
    print("=== Test Free-form Plot & Content Search (Tieng Viet & Tieng Anh) ===")
    uid = "test_plot_user"
    plot_cases = [
        (
            "một phi hành gia bị mắc kẹt trên sao hỏa phải tìm cách sinh tồn",
            {"The Martian", "Red Planet", "Mission to Mars", "Interstellar"},
        ),
        (
            "phim về vụ đắm tàu Titanic lịch sử lãng mạn",
            {"Titanic"},
        ),
        (
            "phim về công viên khủng long tiền sử",
            {"Jurassic World", "Jurassic Park", "The Lost World: Jurassic Park"},
        ),
        (
            "phim về cậu bé phù thủy học phép thuật ở trường",
            {"Harry Potter and the Philosopher's Stone", "Harry Potter and the Prisoner of Azkaban", "Harry Potter and the Chamber of Secrets", "Harry Potter and the Goblet of Fire"},
        ),
        (
            "phim về cá mập tấn công dưới biển",
            {"Jaws", "The Shallows", "Deep Blue Sea", "Shark Night"},
        ),
    ]
    for query, expected_titles in plot_cases:
        res = chat_recommend(uid, query, db_path=DB_PATH, top_n=10, use_llm=False)
        top_titles = [m["title"] for m in res["items"]]
        assert any(t in top_titles for t in expected_titles), (
            f"Plot query {query!r} failed! Expected one of {expected_titles}, got {top_titles[:5]}"
        )
        print(f"  OK plot: {query!r} -> Top-3={top_titles[:3]}")
    print("  Free-form plot & content search passed successfully!\n")


def test_unrecognized_and_gibberish_queries():
    print("=== Test Unrecognized and Gibberish Queries ===")
    uid = "test_gibberish_user"
    gibberish_queries = [
        "dddd",
        "aaaaa",
        "???",
        "123456",
        "thời tiết hôm nay thế nào",
        "bàn ghế tủ lạnh",
    ]
    for q in gibberish_queries:
        try:
            chat_recommend(uid, q, db_path=DB_PATH, use_llm=False)
            raise AssertionError(f"Query {q!r} should have raised ValueError!")
        except ValueError as e:
            print(f"  OK rejected: {q!r:30} -> {e}")
    print("  All gibberish and unrecognized queries properly raised ValueError!\n")


def main():
    print("=====================================================================")
    print("DANH GIA DINH TINH TREN TAP MAU NHO (n = 20 CAU TRUY VAN TIENG VIET/ANH)")
    print("Luu y: Day la danh gia dinh tinh (qualitative evaluation) tren mau nho")
    print("de kiem tra kha nang hieu y dinh, loc the loai tranh va sinh ly do.")
    print("=====================================================================\n")

    test_unrecognized_and_gibberish_queries()
    test_keyword_queries()
    test_freeform_plot_and_content_queries()
    test_multi_turn_and_profile_blending()

    res_local = evaluate_20_queries(use_llm=False)
    print(f"--- 1. CHE DO CUC BO (use_llm=False, khong can API key / mang) ---")
    print(f"  Khop y dinh (Intent Match):        {res_local['intent_matched']}/{res_local['total']}")
    print(f"  Khop the loai Top-5 (Genre Match): {res_local['rec_genre_matched']}/{res_local['total']}")
    print(f"  Vi pham the loai tranh (Avoid):    {res_local['avoid_violated']}/{res_local['total']}\n")

    for r in res_local["rows"]:
        status = "OK" if (r["ok_intent"] and r["ok_rec"] and not r["avoid_violated"]) else "CHECK"
        print(f"  [{r['id']:02d}] ({status}) Q: {r['query']}")
        print(f"       -> {r['summary_line']}")
        print(f"       -> Top-1: {r['top1_title']} {r['top1_genres']} | Lý do: {r['top1_why']}")

    # Kiem tra che do use_llm=True (neu khong co key phai fallback muot ve Local 100%)
    res_llm = evaluate_20_queries(use_llm=True)
    print(f"\n--- 2. CHE DO CO BAT FALLBACK LLM (use_llm=True) ---")
    print(f"  Parser source thuc te:             {res_llm['rows'][0]['parser_source']}")
    print(f"  Khop y dinh (Intent Match):        {res_llm['intent_matched']}/{res_llm['total']}")
    print(f"  Khop the loai Top-5 (Genre Match): {res_llm['rec_genre_matched']}/{res_llm['total']}")
    print(f"  Vi pham the loai tranh (Avoid):    {res_llm['avoid_violated']}/{res_llm['total']}")

    assert res_local["intent_matched"] == 20, f"Expected 20/20 intent match, got {res_local['intent_matched']}"
    assert res_local["rec_genre_matched"] == 20, f"Expected 20/20 genre match, got {res_local['rec_genre_matched']}"
    assert res_local["avoid_violated"] == 0, f"Expected 0 avoid violations, got {res_local['avoid_violated']}"
    print("\n=== ALL 20 QUALITATIVE CHATBOT TESTS PASSED ===")


if __name__ == "__main__":
    main()

