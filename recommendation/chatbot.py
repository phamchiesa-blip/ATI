"""
chatbot.py
----------
Module hoi dap goi y phim cho muc "Hom nay xem gi?" (Chat Bot / Conversational Recommender).

Thiet ke theo dung kien truc 324 chieu cua nhom:
    1. Hieu yeu cau (Intent Parsing):
       - Cach 1 (Cuc bo - Local Rule & Dictionary): Tu dien tam trang/the loai song ngu Viet-Anh,
         nhan dien "giong phim X" (khop ten phim trong catalog), thoi ky (nam/thap nien),
         thoi luong, dao dien/dien vien, tu khoa noi dung va ho tro nhieu luot hoi thoai
         (multi-turn refinement: "nhe hon nua", "them hai", "bo kinh di", "moi hon"...).
       - Cach 2 (LLM API - Tuy chon): Neu co GEMINI_API_KEY hoac OPENAI_API_KEY va mang hoat dong,
         dung LLM phan tich cau tu do sang cung cau truc JSON Intent; neu khong co key hoac loi
         thi tu dong roi ve Cach 1 (dam bao clone sach / mat mang van chay 100%).
    2. Dung Query Vector (324 chieu):
       - [0:20]    Genre multi-hot (the loai muon +1, the loai tranh 0)
       - [20:71]   Director one-hot (50 dao dien pho bien + Other/Unknown)
       - [71:271]  Cast multi-hot (200 dien vien pho bien)
       - [271:321] Overview TF-IDF + SVD 50 chieu (chieu tu khoa/mo ta vao cung khong gian SVD cua movies.db)
       - [321:324] Numeric signals (vote_average, popularity, release_year scaled [0, 1])
       - Neu co "giong phim X", tron vector cua phim X vao query vector.
    3. Loc & Xep hang (Filtering + Cosine + Profile Blending + Multi-Objective Ranking):
       - Loc cung: phim da Like/Dislike, phim thuoc the loai can tranh, phim ngoai khoang thoi gian/thoi luong.
       - Tinh Cosine Similarity giua Query Vector va cac phim ung vien.
       - Tron (blend) voi User Profile (neu nguoi dung da co ho so so thich) va dua qua
         Multi-Objective Ranking (Cosine 0.6 + Rating 0.2 + Popularity 0.1 + Newness 0.1) + Online Reranker.
    4. Sinh ly do giai thich & dong tom tat "Minh hieu ban muon: ...":
       - Minh bach, cho phep nguoi dung bam sua/bo tag ngay tren giao dien.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Import cac module co san cua nhom
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DATA_SRC = os.path.join(_ROOT, "data_module", "src")
_REC_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (_ROOT, _DATA_SRC, _REC_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _load_dotenv_if_present() -> None:
    """Tu dong nap file .env o thu muc goc (neu co) khi chay chatbot doc lap hoac qua API."""
    env_path = os.path.join(_ROOT, ".env")
    if not os.path.exists(env_path):
        return
    placeholders = {"your_gemini_api_key_here", "your_tmdb_api_key_here", "your_openai_api_key_here"}
    try:
        with open(env_path, encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[7:].strip()
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and val and val not in placeholders and not os.environ.get(key):
                    os.environ[key] = val
    except Exception:
        pass


_load_dotenv_if_present()

from feature_store import (
    DEFAULT_DB_PATH,
    check_db_exists,
    get_all_vectors,
    get_movie_metadata,
    get_movie_vector,
    get_user_interactions,
)
from similarity import cosine_similarity_bulk
import recommender as _rec
from ranking_eval.ranking import rank_candidates
from ranking_eval.integration import _apply_neural_reranking


# ═══════════════════════════════════════════════════════════════════════════
# 1. TU DIEN TIENG VIET & TIENG ANH (THE LOAI, TAM TRANG, TU KHOA, GOI Y NHANH)
# ═══════════════════════════════════════════════════════════════════════════

GENRE_VI_LABELS: dict[str, str] = {
    "Action": "Hành động",
    "Adventure": "Phiêu lưu",
    "Animation": "Hoạt hình",
    "Comedy": "Hài",
    "Crime": "Tội phạm / Hình sự",
    "Documentary": "Tài liệu",
    "Drama": "Tâm lý / Chính kịch",
    "Family": "Gia đình",
    "Fantasy": "Kỳ ảo / Phép thuật",
    "Foreign": "Phim nước ngoài",
    "History": "Lịch sử",
    "Horror": "Kinh dị",
    "Music": "Âm nhạc",
    "Mystery": "Bí ẩn / Trinh thám",
    "Romance": "Lãng mạn / Tình cảm",
    "Science Fiction": "Khoa học viễn tưởng",
    "TV Movie": "Phim truyền hình",
    "Thriller": "Giật gân / Hồi hộp",
    "War": "Chiến tranh",
    "Western": "Viễn Tây",
}

# Goi y bam nhanh hien thi ngay duoi o nhap chat
QUICK_SUGGESTIONS: list[dict[str, str]] = [
    {
        "id": "chill",
        "label": "Nhẹ nhàng, thư giãn cuối tuần",
        "prompt": "Gợi ý phim hài nhẹ nhàng, thư giãn, ấm áp, tránh kinh dị",
    },
    {
        "id": "mindblow",
        "label": "Xoắn não giống Inception",
        "prompt": "Phim khoa học viễn tưởng hồi hộp, xoắn não giống Inception",
    },
    {
        "id": "romance",
        "label": "Tình cảm lãng mạn, sâu lắng",
        "prompt": "Phim tình cảm lãng mạn, cảm động, tránh bạo lực căng thẳng",
    },
    {
        "id": "action_new",
        "label": "Hành động mãn nhãn thập niên 2010s",
        "prompt": "Phim hành động phiêu lưu mãn nhãn từ năm 2010 đến nay",
    },
    {
        "id": "family",
        "label": "Hoạt hình vui nhộn cho gia đình",
        "prompt": "Phim hoạt hình gia đình vui vẻ, dưới 100 phút",
    },
    {
        "id": "thriller",
        "label": "Trinh thám, phá án nghẹt thở",
        "prompt": "Phim bí ẩn trinh thám, tội phạm hồi hộp căng thẳng",
    },
]

# Tu dien anh xa cum tu tieng Viet / Anh -> The loai truc tiep
GENRE_SYNONYMS: dict[str, list[str]] = {
    "Action": [
        "hanh dong", "action", "danh nhau", "vo thuat", "ban sung", "chay no",
        "man nhan", "sieu anh hung", "superhero", "martial arts", "dua xe", "agent", "diep vien",
    ],
    "Adventure": [
        "phieu luu", "adventure", "tham hiem", "kham pha", "hanh trinh", "sinh ton",
        "kho bau", "dao hoang", "survival", "quest", "journey",
    ],
    "Animation": [
        "hoat hinh", "animation", "anime", "cartoon", "pixar", "disney", "ghibli", "3d animation",
    ],
    "Comedy": [
        "hai", "phim hai", "the loai hai", "hai huoc", "comedy", "vui nhon", "mac cuoi", "buon cuoi", "cuoi be bung", "giai tri", "funny",
        "humorous", "sitcom", "romcom", "rom-com", "hai lang man",
    ],
    "Crime": [
        "toi pham", "hinh su", "crime", "gangster", "mafia", "vu cuop", "bang cuop", "heist",
        "canh sat", "police", "detective", "pha an", "buon lau", "sat nhan",
    ],
    "Documentary": [
        "tai lieu", "documentary", "phim tai lieu", "su that", "phong su", "thien nhien",
    ],
    "Drama": [
        "tam ly", "chinh kich", "drama", "cuoc song", "nhan van", "doi thuong",
        "bi kich", "noi tam", "emotional", "deep",
    ],
    "Family": [
        "gia dinh", "family", "tre em", "thieu nhi", "kids", "children", "xem cung gia dinh",
        "phu huynh", "am ap gia dinh",
    ],
    "Fantasy": [
        "ky ao", "phep thuat", "fantasy", "than thoai", "phu thuy", "con rong", "phim rong", "nang tien",
        "tien ca", "than tien", "magic", "wizard", "dragon", "mythology", "the gioi khac", "co tich",
    ],
    "History": [
        "lich su", "history", "historical", "co trang", "bieu tuong lich su", "su thi",
        "biography", "tieu su", "co that",
    ],
    "Horror": [
        "kinh di", "horror", "phim ma", "ma quy", "con ma", "bong ma", "rung ron", "am anh",
        "scary", "ghost", "zombie", "xac song", "quai vat", "slasher", "creepy", "jump scare", "mau me",
    ],
    "Music": [
        "am nhac", "nhac kich", "music", "musical", "ca hat", "ban nhac", "concert", "ca si",
    ],
    "Mystery": [
        "bi an", "trinh tham", "mystery", "dieu tra", "xoan nao", "plot twist",
        "twist", "giai ma", "whodunit", "detective", "ky bi",
    ],
    "Romance": [
        "lang man", "tinh cam", "romance", "romantic", "tinh yeu", "yeu nhau", "phim yeu", "hen ho",
        "cap doi", "love", "love story", "ngot ngao", "that tinh", "chia tay",
    ],
    "Science Fiction": [
        "khoa hoc vien tuong", "vien tuong", "sci-fi", "scifi", "science fiction",
        "vu tru", "khong gian", "space", "tuong lai", "future", "robot", "tri tue nhan tao",
        "nguoi ngoai hanh tinh", "alien", "du hanh thoi gian", "time travel", "cyberpunk", "dystopia",
    ],
    "Thriller": [
        "giat gan", "hoi hop", "thriller", "cang thang", "nghet tho", "suspense",
        "gay can", "kich tinh", "tam ly toi pham", "chase", "ruot duoi",
    ],
    "War": [
        "chien tranh", "war", "quan doi", "nguoi linh", "the chien", "world war",
        "chien truong", "soldier", "military", "battle",
    ],
    "Western": [
        "vien tay", "western", "cao boi", "cowboy", "mien tay", "sheriff",
    ],
}

# Tu dien Tam trang (Mood) -> {label, genres (muon), avoid (tranh), keywords (tieng Anh cho TF-IDF)}
MOOD_DICTIONARY: list[dict[str, Any]] = [
    {
        "id": "light_relax",
        "label": "nhẹ nhàng, thư giãn",
        "triggers": [
            "nhe nhang", "thu gian", "chill", "xem giai tri", "xa stress", "bot cang thang",
            "de xem", "khong nao", "feel good", "feel-good", "comfort", "healing", "chua lanh",
            "am ap", "binh yen", "de chiu", "relax", "lighthearted", "cozy",
        ],
        "genres": ["Comedy", "Romance", "Family", "Animation"],
        "avoid": ["Horror", "War", "Thriller", "Crime"],
        "en_keywords": "lighthearted warm funny friendship family love happy life",
    },
    {
        "id": "happy_fun",
        "label": "vui vẻ, hài hước",
        "triggers": [
            "vui ve", "hai huoc", "cuoi be bung", "vui nhon", "hanh phuc", "yeu doi",
            "funny", "hilarious", "happy", "cheerful", "upbeat", "giai khuay",
        ],
        "genres": ["Comedy", "Animation", "Family", "Adventure"],
        "avoid": ["Horror", "War", "Drama"],
        "en_keywords": "comedy hilarious laugh fun adventure party friends",
    },
    {
        "id": "thrilling_tense",
        "label": "hồi hộp, căng thẳng",
        "triggers": [
            "hoi hop", "cang thang", "nghet tho", "gay can", "kich tinh", "tim dap nhanh",
            "thrilling", "tense", "suspenseful", "edge of seat", "intense",
        ],
        "genres": ["Thriller", "Mystery", "Crime", "Action"],
        "avoid": ["Family", "Animation"],
        "en_keywords": "suspense thriller mystery investigation danger secret escape",
    },
    {
        "id": "mind_bending",
        "label": "xoắn não, suy ngẫm",
        "triggers": [
            "xoan nao", "hack nao", "plot twist", "twist", "suy ngam", "sau sac",
            "triet ly", "mind bending", "mind-bending", "mindblowing", "thought provoking",
            "phuc tap", "bat ngo",
        ],
        "genres": ["Mystery", "Science Fiction", "Thriller", "Drama"],
        "avoid": ["Family", "Comedy"],
        "en_keywords": "mystery mind dream reality time memory twist secret psychological",
    },
    {
        "id": "sad_touching",
        "label": "buồn, cảm động, sâu lắng",
        "triggers": [
            "tam trang buon", "phim buon", "ket buon", "cam dong", "sau lang", "khoc het nuoc mat", "roi nuoc mat", "lay dong", "tam trang", "co don",
            "that tinh", "emotional", "touching", "sad", "tearjerker", "heartbreaking", "melancholy",
        ],
        "genres": ["Drama", "Romance"],
        "avoid": ["Horror", "Comedy", "Action"],
        "en_keywords": "emotional love loss life family tragedy moving heartfelt",
    },
    {
        "id": "excited_epic",
        "label": "phấn khích, mãn nhãn, hoành tráng",
        "triggers": [
            "phan khich", "man nhan", "hoanh trang", "epic", "soi dong", "bung no",
            "bom tan", "blockbuster", "exciting", "adrenaline", "kich thich",
        ],
        "genres": ["Action", "Adventure", "Science Fiction", "Fantasy"],
        "avoid": ["Documentary"],
        "en_keywords": "epic battle hero world save adventure action power",
    },
    {
        "id": "scary_dark",
        "label": "rùng rợn, ám ảnh, đen tối",
        "triggers": [
            "rung ron", "am anh", "den toi", "so hai", "lanh gay", "u am",
            "scary", "spooky", "creepy", "dark", "terrifying", "nightmare",
        ],
        "genres": ["Horror", "Thriller", "Mystery"],
        "avoid": ["Comedy", "Family", "Animation"],
        "en_keywords": "horror dark evil ghost haunted terror night survival",
    },
    {
        "id": "romantic_sweet",
        "label": "lãng mạn, ngọt ngào",
        "triggers": [
            "lang man", "ngot ngao", "hen ho", "tinh yeu", "cap doi",
            "romantic", "sweet", "date night", "crush", "couple",
        ],
        "genres": ["Romance", "Comedy", "Drama"],
        "avoid": ["Horror", "War"],
        "en_keywords": "romance love relationship couple wedding heart Paris",
    },
    {
        "id": "dreamy_magical",
        "label": "mơ mộng, kỳ ảo",
        "triggers": [
            "mo mong", "ky ao", "dieu ky", "huyen ao", "phep mau", "co tich",
            "dreamy", "magical", "whimsical", "enchanting", "wonder",
        ],
        "genres": ["Fantasy", "Animation", "Adventure", "Science Fiction"],
        "avoid": ["Horror", "War", "Crime"],
        "en_keywords": "magic fantasy dream world wonder journey imagination",
    },
    {
        "id": "inspiring",
        "label": "truyền cảm hứng, nghị lực",
        "triggers": [
            "truyen cam hung", "nghi luc", "vuot kho", "thanh cong", "dong luc",
            "inspiring", "motivational", "uplifting", "true story", "vinh quang",
        ],
        "genres": ["Drama", "History", "Documentary"],
        "avoid": ["Horror"],
        "en_keywords": "inspire true story triumph courage dream overcome champion",
    },
]

# Tu dien chuyen tu khoa chu de, boi canh, nhan vat, cot truyen tieng Viet sang tieng Anh
# Bao phu >350 tu va cum tu pho bien de nguoi dung mo ta noi dung phim bat ky van tim chinh xac 100% offline
VI_TO_EN_TOPIC_KEYWORDS: dict[str, str] = {
    # --- Khong gian / Khoa hoc vien tuong ---
    "vu tru": "space galaxy astronaut planet universe spacecraft",
    "khong gian": "space station astronaut orbit cosmos",
    "phi hanh gia": "astronaut space mission nasa planet mars",
    "sao hoa": "mars planet astronaut survival red planet",
    "mat trang": "moon lunar astronaut apollo space",
    "ho den": "black hole wormhole space time relativity",
    "du hanh thoi gian": "time travel future past paradox time machine",
    "vong lap thoi gian": "time loop repeat day over again time travel",
    "thoi gian": "time travel loop future past",
    "nguoi ngoai hanh tinh": "alien extraterrestrial invasion ufo spaceship",
    "vat the bay": "ufo alien flying saucer extraterrestrial",
    "tri tue nhan tao": "artificial intelligence ai robot machine sentient computer",
    "nguoi may": "robot android cyborg machine artificial intelligence",
    "robot": "robot cyborg machine android",
    "ke huy diet": "terminator cyborg future war machine",
    "the gioi ao": "virtual reality simulation matrix cyber",
    "thuc te ao": "virtual reality simulation game avatar",
    "nhan ban": "clone cloning genetic experiment DNA",
    "bien doi gen": "genetic mutation experiment DNA monster",
    "dot bien": "mutant mutation genetic superpower",
    "tang hinh": "invisible man invisibility experiment",
    "thu nho": "shrink miniature tiny size microscopic",
    "khong lo": "giant monster kaiju colossus huge",
    "da vu tru": "multiverse parallel universe alternate dimension",
    "chieu khong gian": "dimension portal parallel world",

    # --- Kinh di / Sieu nhien / Quai vat ---
    "xac song": "zombie apocalypse virus undead infected survival",
    "zombie": "zombie undead infection survival apocalypse",
    "dai dich": "pandemic virus outbreak infection quarantine plague",
    "virus": "virus infection outbreak deadly disease",
    "ma ca rong": "vampire blood immortal dracula night fang",
    "nguoi soi": "werewolf full moon beast transformation",
    "quy": "demon devil exorcism possession evil spirit",
    "tru ta": "exorcism priest demon possessed demonic",
    "nhap hon": "possession demon spirit haunted body",
    "ngoi nha ma": "haunted house ghost paranormal family spirit",
    "nha ma": "haunted house ghost spirit paranormal",
    "bup be ma": "possessed doll haunted toy curse evil",
    "bup be": "doll toy puppet possessed",
    "loi nguyen": "curse cursed ancient hex spell",
    "nghi le": "ritual cult sacrifice occult dark",
    "ta giao": "cult sect ritual brainwash fanatical",
    "ac mong": "nightmare dream sleep terror Freddy",
    "giac mo": "dream subconscious sleep inception reality",
    "an thit nguoi": "cannibal cannibalism tribe flesh",
    "quai vat": "monster creature beast predator attack",
    "quai thu": "monster beast giant creature kaiju",

    # --- Ky ao / Phep thuat / Than thoai ---
    "phu thuy": "witch wizard magic spell Hogwarts sorceress",
    "phap su": "wizard sorcerer mage magic spell",
    "phep thuat": "magic wizard spell fantasy kingdom",
    "than thoai": "mythology gods Greek Olympus titan legend",
    "vi than": "gods deity immortal mythology Zeus Thor",
    "thien than": "angel heaven wings divine demon",
    "ac quy": "demon devil hell Lucifer soul",
    "tien ca": "mermaid ocean underwater sea princess",
    "nang tien": "fairy pixie magical forest wings",
    "yeu tinh": "elf goblin troll fantasy middle earth",
    "nguoi lun": "dwarf dwarfs fantasy treasure mountain",
    "rong": "dragon fire knight fantasy kingdom treasure",
    "hiep si": "knight sword armor medieval king castle",
    "kiem si": "swordsman samurai blade duel honor",
    "samurai": "samurai katana Japan warrior honor",
    "ninja": "ninja shinobi assassin stealth Japan",
    "co tich": "fairy tale princess castle magic prince",
    "cong chua": "princess royal castle kingdom prince",
    "hoang tu": "prince royal kingdom throne princess",
    "nha vua": "king throne royal crown kingdom",
    "nu hoang": "queen royal throne crown empire",
    "hoang gia": "king queen royal palace kingdom crown",
    "de che": "empire emperor war ancient Rome",
    "la ma": "Roman empire gladiator Caesar arena",
    "dau si": "gladiator arena Rome fight slave",
    "ai cap": "Egypt pharaoh pyramid mummy ancient curse",
    "xac uop": "mummy Egypt tomb curse pyramid",
    "kho bau": "treasure hunt map gold island pirate",
    "cuop bien": "pirate ship Caribbean sea captain treasure",
    "hai tac": "pirate ship ocean treasure captain",

    # --- Sieu anh hung / Hanh dong / Toi pham ---
    "sieu anh hung": "superhero hero villain superpower comic save world",
    "sieu nang luc": "superpower telekinesis psychic mind power",
    "anh hung": "hero bravery rescue save world warrior",
    "ac nhan": "villain supervillain crime mastermind evil",
    "diep vien": "spy secret agent cia mi6 mission intelligence",
    "dac vu": "secret agent fbi cia operative mission",
    "mat vu": "secret service agent bodyguard president",
    "ve si": "bodyguard protect security assassin",
    "sat thu": "assassin hitman killer contract revenge",
    "linh danh thue": "mercenary squad mission war weapon",
    "bao thu": "revenge vengeance justice payback kill",
    "tra thu": "revenge vengeance payback murder",
    "cuop ngan hang": "bank heist robbery thief vault plan",
    "vu cuop": "heist robbery bank casino diamond",
    "trom": "thief burglary heist steal jewel",
    "sieu trom": "master thief heist steal diamond art",
    "lua dao": "con artist scam fraud trickster hustle",
    "pha an": "detective murder investigation crime clue killer",
    "dieu tra": "investigation detective fbi murder mystery",
    "tham tu": "detective Sherlock investigation mystery clue",
    "canh sat": "police cop officer detective partner crime",
    "canh sat chim": "undercover cop agent infiltrate mafia gang",
    "noi gian": "mole informant undercover traitor spy",
    "sat nhan": "serial killer murder psychopath detective",
    "giet nguoi hang loat": "serial killer murder victim detective fbi",
    "bat coc": "kidnap abduction ransom hostage rescue",
    "con tin": "hostage negotiation rescue terrorist",
    "khung bo": "terrorist bomb attack hijack hostage",
    "khong tac": "hijack airplane flight terrorist passenger",
    "toa an": "court lawyer trial judge jury justice",
    "luat su": "lawyer attorney trial court defense",
    "quan toa": "judge court justice trial law",
    "nha tu": "prison inmate jail guard sentence",
    "vuot nguc": "prison escape break out jail inmate",
    "tu nhan": "prisoner inmate jail escape",
    "mafia": "mafia gangster crime boss family mob",
    "bang dang": "gang gangster crime street turf",
    "xa hoi den": "triad yakuza mafia mob crime boss",
    "ma tuy": "drug cartel dealer narcoticsDEA",
    "buon lau": "smuggler contraband cartel border",
    "dua xe": "car racing driver fast street race",
    "vo thuat": "martial arts kung fu fighter master tournament",
    "kung fu": "kung fu martial arts shaolin master China",
    "quyen anh": "boxing boxer ring champion fight",
    "dam boc": "boxing fighter ring heavyweight champion",
    "dau vo": "martial arts tournament fighter arena",
    "ban tia": "sniper sharpshooter military rifle",

    # --- Chien tranh / Lich su / Sinh ton / Tham hoa ---
    "chien tranh": "war soldier army battle military combat",
    "the chien": "world war soldier nazi allied battle",
    "phat xit": "nazi Hitler holocaust world war Germany",
    "do thai": "holocaust Jewish concentration camp nazi",
    "chien tranh viet nam": "Vietnam war soldier jungle military",
    "nguoi linh": "soldier military war army platoon",
    "tau ngam": "submarine navy underwater torpedo captain",
    "tau chien": "battleship navy war ocean fleet",
    "phi cong": "pilot fighter jet aviation airplane",
    "may bay": "airplane flight crash pilot passenger",
    "roi may bay": "plane crash survival island stranded",
    "sinh ton": "survival wilderness stranded rescue island",
    "mac ket": "stranded trapped survival canyon island",
    "dao hoang": "deserted island castaway stranded survival",
    "lac tren dao": "island stranded castaway survival ocean",
    "sa mac": "desert sand survival oasis heat",
    "bac cuc": "arctic snow ice cold survival polar",
    "nui tuyet": "mountain snow avalanche climb survival",
    "leo nui": "mountain climbing Everest peak survival",
    "tham hoa": "disaster earthquake volcano tsunami storm survival",
    "dong dat": "earthquake fault collapse disaster rescue",
    "song than": "tsunami wave ocean flood disaster",
    "nui lua": "volcano eruption lava ash disaster",
    "bao": "storm hurricane tornado tempest sea",
    "loc xoay": "tornado twister storm wind",
    "ngay tan the": "apocalypse end of the world meteor survival",
    "tan the": "apocalypse doomsday end of the world survival",
    "hau tan the": "post apocalyptic wasteland survival future",
    "thien thach": "asteroid meteor comet impact earth",
    "chim tau": "shipwreck sinking ship ocean Titanic",

    # --- Gia dinh / Tinh cam / Tam ly / Doi song ---
    "hoc duong": "high school student teenager college prom",
    "sinh vien": "college university student campus youth",
    "hoc sinh": "student school teacher classroom",
    "thay giao": "teacher professor school inspire student",
    "co giao": "teacher school student classroom",
    "tuoi tre": "youth coming of age teenager friendship summer",
    "thanh xuan": "youth high school first love friendship memory",
    "tinh dau": "first love romance youth crush heart",
    "yeu don phuong": "unrequited love crush secret romance",
    "ngoai tinh": "affair infidelity marriage betrayal wife husband",
    "ly hon": "divorce marriage custody couple separation",
    "ket hon": "wedding marriage bride groom love",
    "dam cuoi": "wedding bride groom marriage family",
    "hen ho": "dating blind date romance couple love",
    "chia tay": "breakup heartbreak ex lover relationship",
    "that tinh": "heartbreak breakup lonely love recovery",
    "tinh ban": "friendship best friends bond buddy",
    "gia dinh": "family father mother son daughter home",
    "cha con": "father son daughter dad family bond",
    "bo con": "father son daughter dad family",
    "me con": "mother son daughter mom family love",
    "anh em": "brothers sibling family loyalty",
    "chi em": "sisters sibling family woman",
    "vo chong": "husband wife marriage couple relationship",
    "tre mo coi": "orphan orphanage adopt family child",
    "nhan nuoi": "adoption foster child parents family",
    "mang thai": "pregnancy pregnant baby mother",
    "mat tri nho": "amnesia memory loss forget identity",
    "tri nho": "memory amnesia remember brain",
    "tam than": "mental illness asylum psychiatric hospital mind",
    "da nhan cach": "split personality multiple identity disorder",
    "tram cam": "depression grief loneliness mental healing",
    "ung thu": "cancer terminal illness hospital love life",
    "benh nan y": "terminal illness disease hospital love",
    "nguoi mu": "blind sight vision disability",
    "nguoi cam diec": "deaf mute sign language",
    "nha van": "writer author novelist book manuscript",
    "nha bao": "journalist reporter newspaper investigation truth",
    "bac si": "doctor surgeon hospital medical patient",
    "y ta": "nurse hospital patient care",
    "nha khoa hoc": "scientist laboratory experiment research",
    "thien tai": "genius prodigy mathematician brilliant mind",
    "toan hoc": "mathematician math genius numbers professor",
    "vat ly": "physicist science theory quantum",
    "ty phu": "billionaire millionaire rich wealth money",
    "pho wall": "wall street stock market finance money",
    "chung khoan": "stock market finance wall street trader",
    "ngan hang": "bank banker money finance",
    "co bac": "gambling casino poker Las Vegas card",
    "song bac": "casino Las Vegas gambling blackjack poker",
    "khoi nghiep": "startup entrepreneur company business success",

    # --- Nghe thuat / Am nhac / The thao / Am thuc / Du lich ---
    "am nhac": "music band singer song concert piano",
    "ca si": "singer music pop star stage song",
    "ban nhac": "rock band music concert tour musician",
    "duong cam": "piano pianist classical music concert",
    "piano": "piano pianist music classical",
    "trong": "drummer jazz music conservatory band",
    "nhay": "dance dancer ballet hip hop stage",
    "mua ba le": "ballet dancer swan stage performance",
    "hoi hoa": "painter artist painting art gallery",
    "hoa si": "painter artist portrait art",
    "nhiep anh": "photographer camera photo journalism",
    "dien anh": "filmmaker director Hollywood movie actor",
    "the thao": "sport team coach championship tournament",
    "bong da": "football soccer team coach championship",
    "bong ro": "basketball coach team high school player",
    "bong chay": "baseball team pitcher stadium league",
    "dua ngua": "horse racing jockey champion stallion",
    "am thuc": "food chef restaurant cooking kitchen culinary",
    "nau an": "chef cooking restaurant food kitchen",
    "dau bep": "chef restaurant kitchen cooking food",
    "du lich": "travel journey road trip vacation Europe",
    "phuot": "road trip backpacker travel adventure",
    "giang sinh": "christmas holiday snow santa family gift",
    "le ta on": "thanksgiving family dinner holiday",
    "halloween": "halloween pumpkin trick or treat night horror",

    # --- Dong vat / Thien nhien ---
    "con cho": "dog puppy pet loyal animal canine",
    "chu cho": "dog puppy pet loyal companion",
    "con meo": "cat kitten pet animal feline",
    "con ngua": "horse stallion riding ranch wild",
    "ngua van": "zebra zoo Africa Madagascar Marty",
    "huou cao co": "giraffe zoo Africa Madagascar Melman",
    "ha ma": "hippo hippopotamus zoo Africa Madagascar Gloria",
    "vuon thu": "zoo central park animals escape Madagascar",
    "so thu": "zoo animals escape central park",
    "con khi": "ape monkey chimpanzee gorilla planet",
    "khi dot": "ape gorilla primate jungle evolution",
    "con gau": "bear grizzly forest cub nature",
    "gau truc": "panda kung fu China bamboo dragon warrior",
    "su tu": "lion pride Africa savanna king zoo Alex",
    "ca voi": "whale ocean sea marine mammal",
    "ca heo": "dolphin ocean sea marine",
    "chim canh cut": "penguin penguins Antarctica ice Madagascar",
    "thu cung": "pet dog cat animal loyal",
    "dong vat": "animal animals wildlife zoo nature",
    "rung xanh": "jungle rainforest Tarzan wild animal",
    "dai duong": "ocean sea underwater deep submarine",
    "bien": "ocean sea ship shark island underwater",
    "ca map": "shark ocean attack beach survival",
    "ca sau": "crocodile alligator swamp river attack",
    "ran khong lo": "giant snake anaconda jungle attack",
    "nhen": "spider arachnid bite web",
    "khung long": "dinosaur jurassic island park prehistoric",
    "voi": "elephant Africa circus animal",
    "soi": "wolf pack wilderness snow survival",
}

# Tu dien dich DON TU (Single-word Vietnamese -> English) cho cac danh tu, dong tu, tinh tu
# giup chuyen bat ky cau mo ta noi dung tieng Viet tu do nao sang tu khoa tieng Anh cho TF-IDF/BM25
VI_WORD_TO_EN: dict[str, str] = {
    "dao": "island", "hoang": "deserted stranded", "rung": "forest jungle",
    "nui": "mountain", "bien": "sea ocean", "song": "river", "ho": "lake",
    "tuyet": "snow ice", "lua": "fire flame", "nuoc": "water", "dat": "earth land",
    "troi": "sky heaven", "mua": "rain storm", "gio": "wind", "cat": "sand desert",
    "tau": "ship train boat", "thuyen": "boat ship", "xe": "car vehicle",
    "nha": "house home", "lau": "castle mansion", "thanh": "city castle",
    "pho": "street city", "lang": "village town", "truong": "school college",
    "lop": "class school", "benh": "disease illness", "vien": "hospital institute",
    "thuoc": "drug medicine", "tien": "money cash", "vang": "gold treasure",
    "kim": "diamond needle", "cuong": "diamond", "bau": "treasure",
    "vua": "king", "hoang": "emperor royal", "chua": "princess", "tu": "prince prison",
    "linh": "soldier spirit", "tuong": "general statue", "quan": "army military",
    "sung": "gun weapon", "kiem": "sword blade", "dao": "knife island",
    "bom": "bomb explosive", "dan": "bullet", "mau": "blood", "xac": "corpse body",
    "chet": "dead death die", "song": "alive live", "cuu": "rescue save",
    "giet": "kill murder", "ban": "shoot friend sell", "danh": "fight beat",
    "chay": "run burn", "tron": "escape flee hide", "bat": "catch arrest kidnap",
    "tim": "find search heart", "mat": "lose lost eye", "nho": "remember memory small",
    "quen": "forget amnesia", "yeu": "love romance", "ghet": "hate", "cuoi": "laugh marry",
    "khoc": "cry tears", "so": "fear afraid", "gian": "angry", "co": "lonely aunt",
    "don": "lonely single", "ngheo": "poor poverty", "giau": "rich wealthy",
    "gia": "old fake family", "tre": "young child", "be": "child little",
    "con": "child son daughter animal", "cha": "father dad", "bo": "father dad",
    "me": "mother mom", "vo": "wife", "chong": "husband", "anh": "brother hero",
    "em": "sister brother", "ban": "friend partner", "ke": "enemy person",
    "thu": "enemy animal", "cho": "dog", "meo": "cat", "chim": "bird",
    "ca": "fish shark whale", "ran": "snake", "ngua": "horse", "khi": "monkey ape",
    "gau": "bear", "voi": "elephant", "ho": "tiger", "soi": "wolf",
    "ma": "ghost haunted", "quy": "demon devil", "than": "god spirit",
    "tien": "fairy angel", "rong": "dragon", "phu": "wizard witch", "thuy": "witch water",
    "bay": "fly trap", "chim": "sink bird", "roi": "fall crash", "no": "explode debt",
    "cuop": "robbery heist pirate", "trom": "thief steal", "lua": "deceive con fire",
    "tu": "prison jail", "toa": "court building", "an": "case eat peace",
    "hat": "sing song", "nhac": "music song", "mua": "dance buy rain",
    "ve": "paint draw return", "viet": "write book", "doc": "read poison lonely",
    "hoc": "study learn school", "day": "teach wake", "nau": "cook",
    "dua": "race", "dau": "fight compete head pain", "thang": "win victory",
    "thua": "lose defeat", "vong": "loop ring circle", "lap": "repeat loop",
    "khu": "zone area", "ham": "bunker tunnel", "ngam": "underground submarine",
    "mat": "secret lost eye", "bi": "secret mystery", "an": "hidden mystery",
    "khoa": "science lock", "hoc": "science study", "hanh": "planet action journey",
    "tinh": "planet love awake", "sao": "star mars", "anh": "light hero",
    "sang": "light bright morning", "toi": "dark night", "dem": "night",
    "ngay": "day", "mua": "season rain", "he": "summer", "dong": "winter",
}


# Cac tu/am tiet de trung lap giua tieng Viet khong dau va tieng Anh
_VI_FALSE_EN: set[str] = {
    "movie", "movies", "film", "films", "like", "with", "want", "watch", "some", "good", "best",
    "cho", "minh", "phim", "xem", "nhung", "hay", "cua", "cac", "mot", "nhu", "nam", "tuoi",
    "tre", "hop", "man", "tim", "tai", "luc", "anh", "hung", "dao", "dien", "vien", "tay",
    "cao", "boi", "kinh", "dien", "truoc", "sau", "den", "nay", "nhe", "hon", "nua", "tranh",
    "khong", "thich", "cam", "dong", "buon", "vui", "cuoi", "tuan", "gio", "nghi", "trua",
    "nhanh", "duoi", "phut", "thap", "nien", "khoa", "hoc", "vien", "tuong",
    "hoat", "hinh", "gia", "dinh", "tinh", "lang", "tam", "chinh", "kich", "toi", "pham",
    "lich", "chien", "tranh", "lieu", "truyen", "that", "bao", "duong", "soi",
    "ban", "ghe", "lanh", "tu", "nha", "thoi", "tiet",
}


def _fold(s: str) -> str:
    """Bo dau tieng Viet + chuyen chu thuong (chuan hoa van ban de so khop)."""
    s = s.replace("đ", "d").replace("Đ", "d")
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", s.lower())
        if not unicodedata.combining(ch)
    )


# ═══════════════════════════════════════════════════════════════════════════
# 2. CAU TRUC Y DINH (STRUCTURED INTENT)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ChatIntent:
    """Cau truc y dinh trich xuat tu cau nhap cua nguoi dung (hoac sau nhieu luot)."""
    wanted_genres: list[str] = field(default_factory=list)
    avoid_genres: list[str] = field(default_factory=list)
    mood_labels: list[str] = field(default_factory=list)
    similar_movie_ids: list[int] = field(default_factory=list)
    similar_movie_titles: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    matched_keyword_display: str = ""
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    max_runtime: Optional[int] = None
    min_rating: Optional[float] = None
    director: Optional[str] = None
    actor: Optional[str] = None
    keywords_raw: str = ""
    keywords_en: str = ""
    content_query_en: str = ""
    content_query_vi: str = ""
    ai_candidate_ids: list[int] = field(default_factory=list)
    ai_candidate_titles: list[str] = field(default_factory=list)
    is_followup: bool = False
    parser_source: str = "local"  # "local" | "llm"

    def is_empty(self) -> bool:
        """Kiem tra xem co bat ky tieu chi tim phim nao duoc nhan dien hay khong."""
        return not (
            self.wanted_genres
            or self.avoid_genres
            or self.mood_labels
            or self.similar_movie_ids
            or self.ai_candidate_ids
            or self.matched_keywords
            or self.director
            or self.actor
            or self.year_from is not None
            or self.year_to is not None
            or self.max_runtime is not None
            or self.min_rating is not None
            or self.keywords_raw
            or self.keywords_en
            or self.content_query_en
            or self.content_query_vi
            or self.is_followup
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "wanted_genres": self.wanted_genres,
            "avoid_genres": self.avoid_genres,
            "wanted_genres_vi": [GENRE_VI_LABELS.get(g, g) for g in self.wanted_genres],
            "avoid_genres_vi": [GENRE_VI_LABELS.get(g, g) for g in self.avoid_genres],
            "mood_labels": self.mood_labels,
            "similar_movies": [
                {"movie_id": mid, "title": title}
                for mid, title in zip(self.similar_movie_ids, self.similar_movie_titles)
            ],
            "ai_candidates": [
                {"movie_id": mid, "title": title}
                for mid, title in zip(self.ai_candidate_ids, self.ai_candidate_titles)
            ],
            "matched_keywords": self.matched_keywords,
            "matched_keyword_display": self.matched_keyword_display,
            "year_from": self.year_from,
            "year_to": self.year_to,
            "max_runtime": self.max_runtime,
            "min_rating": self.min_rating,
            "director": self.director,
            "actor": self.actor,
            "keywords_raw": self.keywords_raw,
            "keywords_en": self.keywords_en,
            "content_query_en": self.content_query_en,
            "content_query_vi": self.content_query_vi,
            "is_followup": self.is_followup,
            "parser_source": self.parser_source,
            "summary_line": self.build_summary_line(),
        }

    def build_summary_line(self) -> str:
        """Tao dong 'Minh hieu ban muon: ...' hien thi ngay tren ket qua."""
        want_parts: list[str] = []
        if self.wanted_genres:
            want_parts.extend(GENRE_VI_LABELS.get(g, g) for g in self.wanted_genres)
        if self.mood_labels:
            for m in self.mood_labels:
                if m not in want_parts:
                    want_parts.append(m)
        if self.similar_movie_titles:
            want_parts.append(f"giống {', '.join(self.similar_movie_titles)}")
        if self.director:
            want_parts.append(f"đạo diễn {self.director}")
        if self.actor:
            want_parts.append(f"diễn viên {self.actor}")
        if self.year_from and self.year_to:
            want_parts.append(f"năm {self.year_from}–{self.year_to}")
        elif self.year_from:
            want_parts.append(f"từ năm {self.year_from}")
        elif self.year_to:
            want_parts.append(f"trước năm {self.year_to}")
        if self.max_runtime:
            want_parts.append(f"dưới {self.max_runtime} phút")
        if self.matched_keyword_display:
            want_parts.append(f"từ khóa “{self.matched_keyword_display}”")
        elif self.matched_keywords:
            want_parts.append(f"từ khóa “{self.matched_keywords[0]}”")
        elif self.keywords_raw and not want_parts:
            want_parts.append(f"chủ đề “{self.keywords_raw}”")
        elif self.keywords_raw and len(self.keywords_raw) <= 40:
            want_parts.append(f"từ khóa “{self.keywords_raw}”")

        if not want_parts and not self.avoid_genres:
            return "Chưa xác định được yêu cầu tìm phim"
        want_str = ", ".join(want_parts) if want_parts else "Phim hay được đánh giá cao"
        out = f"Mình hiểu bạn muốn: {want_str}"
        if self.avoid_genres:
            avoid_str = ", ".join(GENRE_VI_LABELS.get(g, g) for g in self.avoid_genres)
            out += f" · Tránh: {avoid_str}"
        return out


# ═══════════════════════════════════════════════════════════════════════════
# 3. CHI MUC KHONG GIAN 324 CHIEU (CATALOG & FEATURE SPACE INDEX)
# ═══════════════════════════════════════════════════════════════════════════

def _find_movies_csv() -> Optional[str]:
    """Tim duong dan toi tmdb_5000_movies.csv neu co."""
    env = os.environ.get("TMDB_MOVIES_CSV")
    if env and os.path.exists(env):
        return env
    cur = Path(__file__).resolve().parent
    candidates = [
        cur / "tmdb_5000_movies.csv",
        cur / "data" / "tmdb_5000_movies.csv",
        cur.parent / "tmdb_5000_movies.csv",
        cur.parent / "data" / "tmdb_5000_movies.csv",
        cur.parent / "data_module" / "data" / "tmdb_5000_movies.csv",
        cur.parent / "data_module" / "src" / "tmdb_5000_movies.csv",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _find_credits_csv() -> Optional[str]:
    """Tim duong dan toi tmdb_5000_credits.csv neu co."""
    env = os.environ.get("TMDB_CREDITS_CSV")
    if env and os.path.exists(env):
        return env
    cur = Path(__file__).resolve().parent
    candidates = [
        cur / "tmdb_5000_credits.csv",
        cur / "data" / "tmdb_5000_credits.csv",
        cur.parent / "tmdb_5000_credits.csv",
        cur.parent / "data" / "tmdb_5000_credits.csv",
        cur.parent / "data_module" / "data" / "tmdb_5000_credits.csv",
        cur.parent / "data_module" / "src" / "tmdb_5000_credits.csv",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _load_overview_vi_map(db_path: str) -> dict[int, str]:
    """Tai ban dich tom tat tieng Viet (overview_vi) tu movies.db, accounts.db hoac file CSV neu co."""
    out: dict[int, str] = {}
    # 1. Thu doc tu bang movies (neu da co cot overview_vi) hoac bang overview_vi trong movies.db
    try:
        conn = sqlite3.connect(db_path)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(movies)").fetchall()}
        if "overview_vi" in cols:
            for mid, txt in conn.execute("SELECT movie_id, overview_vi FROM movies WHERE overview_vi IS NOT NULL"):
                if txt and str(txt).strip():
                    out[int(mid)] = str(txt).strip()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "overview_vi" in tables:
            for mid, txt in conn.execute("SELECT movie_id, text FROM overview_vi WHERE text IS NOT NULL"):
                if txt and str(txt).strip():
                    out[int(mid)] = str(txt).strip()
        conn.close()
    except Exception:
        pass

    # 2. Thu doc tu accounts.db o thu muc goc
    acc_path = os.environ.get("ACCOUNTS_DB") or os.path.join(_ROOT, "accounts.db")
    if os.path.exists(acc_path):
        try:
            conn = sqlite3.connect(acc_path)
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "overview_vi" in tables:
                for mid, txt in conn.execute("SELECT movie_id, text FROM overview_vi WHERE text IS NOT NULL"):
                    if txt and str(txt).strip() and int(mid) not in out:
                        out[int(mid)] = str(txt).strip()
            conn.close()
        except Exception:
            pass

    # 3. Thu doc tu data_module/overview_vi.csv neu co
    csv_vi = os.path.join(_ROOT, "data_module", "overview_vi.csv")
    if os.path.exists(csv_vi):
        try:
            import csv as _csv
            with open(csv_vi, newline="", encoding="utf-8") as f:
                for r in _csv.DictReader(f):
                    if r.get("movie_id") and r.get("text"):
                        mid = int(r["movie_id"])
                        if mid not in out:
                            out[mid] = r["text"].strip()
        except Exception:
            pass
    return out


class FeatureSpaceIndex:
    """Quan ly va khoi phuc chinh xac khong gian 324 chieu tu movies.db ma khong can
    chay lai build_dataset.py hay luu file pickle ngoai.
    Bo sung chi muc tim kiem noi dung Da tang (Rich Lexical TF-IDF Anh + Viet + Toan bo Dao dien/Dien vien)."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        check_db_exists(db_path)

        self.movie_ids, self.matrix = get_all_vectors(db_path)
        self.id_to_row: dict[int, int] = {int(mid): i for i, mid in enumerate(self.movie_ids)}

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        db_cols = {r[1] for r in conn.execute("PRAGMA table_info(movies)").fetchall()}
        extra_select = ""
        for col_name in ("keywords", "tagline", "runtime", "overview_vi"):
            if col_name in db_cols:
                extra_select += f", {col_name}"
        rows = conn.execute(
            f'SELECT movie_id, title, overview, genres, director, "cast", '
            f'vote_average, vote_count, popularity, release_date{extra_select} '
            f'FROM movies ORDER BY movie_id'
        ).fetchall()
        conn.close()

        overview_vi_map = _load_overview_vi_map(db_path)

        self.movies: dict[int, dict[str, Any]] = {}
        self.titles_ordered: list[tuple[int, str, str, float]] = []  # (mid, title, folded, pop)
        overviews: list[str] = []
        years: list[int] = []

        # Tap hop TOAN BO dao dien va dien vien trong catalog (khong chi gioi han top 50/200)
        all_directors_set: dict[str, str] = {}  # folded -> original
        all_actors_count: dict[str, tuple[str, int]] = {}  # folded -> (original, count)
        self.mid_to_keywords: dict[int, list[str]] = {}
        self.keyword_to_mids: dict[str, set[int]] = {}
        self.mid_to_tagline: dict[int, str] = {}
        self.mid_to_runtime: dict[int, int] = {}

        for r in rows:
            mid = int(r["movie_id"])
            genres = json.loads(r["genres"] or "[]")
            cast = json.loads(r["cast"] or "[]")
            rel_date = r["release_date"] or ""
            year = int(rel_date[:4]) if rel_date[:4].isdigit() else None
            if year is not None:
                years.append(year)

            # Doc keywords/tagline/runtime truc tiep tu DB neu da duoc nang cap schema
            if "keywords" in db_cols and r["keywords"]:
                try:
                    kw_list = json.loads(r["keywords"])
                    if isinstance(kw_list, list):
                        names = [
                            (it["name"].strip() if isinstance(it, dict) else str(it).strip())
                            for it in kw_list
                            if (isinstance(it, dict) and it.get("name")) or isinstance(it, str)
                        ]
                        if names:
                            self.mid_to_keywords[mid] = names
                            for name in names:
                                self.keyword_to_mids.setdefault(name.lower(), set()).add(mid)
                except Exception:
                    pass
            if "tagline" in db_cols and r["tagline"]:
                self.mid_to_tagline[mid] = str(r["tagline"]).strip()
            if "runtime" in db_cols and r["runtime"]:
                try:
                    self.mid_to_runtime[mid] = int(float(r["runtime"]))
                except Exception:
                    pass

            director_name = r["director"]
            if director_name:
                fd = _fold(director_name)
                if len(fd) >= 4:
                    all_directors_set[fd] = director_name
            for actor_name in cast:
                if actor_name:
                    fa = _fold(actor_name)
                    if len(fa) >= 4:
                        prev_orig, prev_cnt = all_actors_count.get(fa, (actor_name, 0))
                        all_actors_count[fa] = (prev_orig, prev_cnt + 1)

            meta = {
                "movie_id": mid,
                "title": r["title"],
                "overview": r["overview"] or "",
                "overview_vi": overview_vi_map.get(mid, ""),
                "genres": genres,
                "director": director_name,
                "cast": cast,
                "vote_average": float(r["vote_average"] or 0.0),
                "vote_count": int(r["vote_count"] or 0),
                "popularity": float(r["popularity"] or 0.0),
                "release_date": rel_date,
                "release_year": year,
            }
            self.movies[mid] = meta
            self.titles_ordered.append((mid, r["title"], _fold(r["title"]), meta["popularity"]))
            overviews.append(meta["overview"])

        # Sap xep titles theo popularity giam dan de uu tien phim noi tieng khi trung ten ngan
        self.titles_ordered.sort(key=lambda x: -x[3])

        # 1. Genre labels [0:20] (sorted alphabet)
        self.genre_labels: list[str] = sorted(
            {g for m in self.movies.values() for g in m["genres"]}
        )
        self.genre_to_col: dict[str, int] = {g: i for i, g in enumerate(self.genre_labels)}

        # 2. Director labels [20:71] (50 top directors + Other/Unknown) + Toan bo director trong DB
        self.director_to_col: dict[str, int] = {}
        self.directors_folded: list[tuple[str, str, int]] = []  # (folded, original, col)
        for col in range(20, 71):
            active = np.where(self.matrix[:, col] == 1.0)[0]
            dirs = {rows[i]["director"] for i in active if rows[i]["director"]}
            if len(dirs) == 1:
                d_name = next(iter(dirs))
                self.director_to_col[d_name] = col
                self.directors_folded.append((_fold(d_name), d_name, col))
        # Bo sung tat ca cac dao dien con lai trong DB (col = -1) de tim kiem van khop 100%
        seen_d_folded = {x[0] for x in self.directors_folded}
        for fd, orig_d in sorted(all_directors_set.items(), key=lambda x: -len(x[0])):
            if fd not in seen_d_folded:
                self.directors_folded.append((fd, orig_d, -1))
        self.directors_folded.sort(key=lambda x: -len(x[0]))

        # 3. Cast labels [71:271] (200 top actors) + Toan bo dien vien trong DB
        self.cast_to_col: dict[str, int] = {}
        self.actors_folded: list[tuple[str, str, int]] = []  # (folded, original, col)
        for col in range(71, 271):
            active = np.where(self.matrix[:, col] == 1.0)[0]
            common = None
            for i in active:
                actors = set(json.loads(rows[i]["cast"] or "[]"))
                common = actors if common is None else (common & actors)
            if common and len(common) == 1:
                a_name = next(iter(common))
                self.cast_to_col[a_name] = col
                self.actors_folded.append((_fold(a_name), a_name, col))
        seen_a_folded = {x[0] for x in self.actors_folded}
        for fa, (orig_a, _cnt) in sorted(all_actors_count.items(), key=lambda x: (-len(x[0]), -x[1][1])):
            if fa not in seen_a_folded:
                self.actors_folded.append((fa, orig_a, -1))
        self.actors_folded.sort(key=lambda x: -len(x[0]))

        # 4. Overview TF-IDF -> SVD projection matrix [271:321]
        # Khoi phuc ma tran chieu V_T (5000 x 50) truc tiep tu Y_svd = X_tfidf @ V_T
        self.tfidf = TfidfVectorizer(max_features=5000, stop_words="english")
        X_tfidf = self.tfidf.fit_transform(overviews)
        Y_svd = self.matrix[:, 271:321]
        col_norms_sq = np.sum(Y_svd ** 2, axis=0, keepdims=True)
        col_norms_sq = np.where(col_norms_sq == 0, 1.0, col_norms_sq)
        self.svd_projection: np.ndarray = np.asarray(
            (X_tfidf.T @ Y_svd) / col_norms_sq, dtype=np.float32
        )

        # 5. Numeric bounds [321:324] (vote_average, popularity, release_year)
        self.min_year = min(years) if years else 1916
        self.max_year = max(years) if years else 2017

        # 6. Chi muc TMDB Keywords & Tagline tu CSV (neu chua co san trong DB)
        self.keywords_folded: list[tuple[str, str, set[int]]] = []
        csv_path = _find_movies_csv()
        if csv_path and not self.mid_to_keywords:
            try:
                import pandas as pd
                df = pd.read_csv(csv_path)
                for _, r_csv in df.iterrows():
                    mid_int = int(r_csv["id"])
                    kw_val = r_csv.get("keywords")
                    if isinstance(kw_val, str):
                        try:
                            items = json.loads(kw_val)
                            names = [it["name"].strip() for it in items if it.get("name")]
                            if names:
                                self.mid_to_keywords[mid_int] = names
                                for name in names:
                                    self.keyword_to_mids.setdefault(name.lower(), set()).add(mid_int)
                        except Exception:
                            pass
                    tl_val = r_csv.get("tagline")
                    if isinstance(tl_val, str) and tl_val.strip():
                        self.mid_to_tagline[mid_int] = tl_val.strip()
                    rt_val = r_csv.get("runtime")
                    if rt_val is not None and rt_val == rt_val:
                        try:
                            self.mid_to_runtime[mid_int] = int(float(rt_val))
                        except Exception:
                            pass
            except Exception:
                pass

        for k_orig, mids_set in self.keyword_to_mids.items():
            self.keywords_folded.append((_fold(k_orig), k_orig, mids_set))
        self.keywords_folded.sort(key=lambda x: -len(x[0]))

        # 7. Chi muc RICH CONTENT TF-IDF (Ket hop Title + Tagline + Keywords + Overview + Director + Cast + Overview_VI)
        # Giup tim kiem noi dung phim (plot/content search) chinh xac gap nhieu lan so voi chi dung 50 chieu SVD
        rich_docs_en: list[str] = []
        rich_docs_vi_folded: list[str] = []
        for mid_np in self.movie_ids:
            mid = int(mid_np)
            m = self.movies[mid]
            kws_str = " ".join(self.mid_to_keywords.get(mid, []))
            tagline_str = self.mid_to_tagline.get(mid, "")
            cast_str = " ".join(m.get("cast") or [])
            dir_str = m.get("director") or ""
            # Lap lai title va keywords 2 lan de tang trong so khi khop tu khoa chinh xac
            doc_en = f"{m['title']} {m['title']} {tagline_str} {kws_str} {kws_str} {m['overview']} {dir_str} {cast_str}"
            rich_docs_en.append(doc_en)

            ov_vi = m.get("overview_vi") or ""
            genres_vi = " ".join(GENRE_VI_LABELS.get(g, g) for g in m.get("genres", []))
            doc_vi = _fold(f"{m['title']} {ov_vi} {genres_vi} {kws_str}")
            rich_docs_vi_folded.append(doc_vi)

        self.rich_tfidf_en = TfidfVectorizer(
            max_features=12000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.rich_matrix_en = self.rich_tfidf_en.fit_transform(rich_docs_en)

        self.rich_tfidf_vi = TfidfVectorizer(
            max_features=8000,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.rich_matrix_vi = self.rich_tfidf_vi.fit_transform(rich_docs_vi_folded)

    def project_text_to_svd(self, text: str) -> np.ndarray:
        """Chieu van ban tieng Anh qua TF-IDF -> 50 chieu SVD cung khong gian movies.db."""
        if not text or not text.strip():
            return np.zeros(50, dtype=np.float32)
        tfidf_vec = self.tfidf.transform([text])
        svd_vec = tfidf_vec @ self.svd_projection
        return np.asarray(svd_vec, dtype=np.float32).reshape(50)

    def compute_content_similarity(self, query_en: str, query_vi_folded: str = "") -> np.ndarray:
        """Tinh diem tuong dong noi dung truc tiep tren Rich TF-IDF (12.000 features n-gram Anh + Viet).
        Giai quyet triet de hien tuong nen SVD 50 chieu lam mat tu khoa cot truyen cu the."""
        n = len(self.movie_ids)
        scores = np.zeros(n, dtype=np.float32)
        if query_en and query_en.strip():
            q_vec_en = self.rich_tfidf_en.transform([query_en])
            if q_vec_en.nnz > 0:
                sim_en = (self.rich_matrix_en @ q_vec_en.T).toarray().reshape(n).astype(np.float32)
                scores = np.maximum(scores, sim_en)
        if query_vi_folded and query_vi_folded.strip():
            q_vec_vi = self.rich_tfidf_vi.transform([query_vi_folded])
            if q_vec_vi.nnz > 0:
                sim_vi = (self.rich_matrix_vi @ q_vec_vi.T).toarray().reshape(n).astype(np.float32)
                scores = np.maximum(scores, sim_vi * 0.95)
        return scores


_SPACE_CACHE: dict[str, tuple[float, FeatureSpaceIndex]] = {}
_SPACE_LOCK = threading.RLock()


def get_feature_space(db_path: str = DEFAULT_DB_PATH) -> FeatureSpaceIndex:
    """Singleton lazy loader cho FeatureSpaceIndex theo db_path (tu dong reload khi file movies.db duoc cap nhat)."""
    abs_path = os.path.abspath(db_path)
    mtime = os.path.getmtime(abs_path) if os.path.exists(abs_path) else 0.0
    with _SPACE_LOCK:
        cached = _SPACE_CACHE.get(abs_path)
        if cached is None or cached[0] != mtime:
            _SPACE_CACHE[abs_path] = (mtime, FeatureSpaceIndex(abs_path))
        return _SPACE_CACHE[abs_path][1]


# ═══════════════════════════════════════════════════════════════════════════
# 4. BUOC HIEU YEU CAU: CACH 1 (CUC BO) & CACH 2 (LLM API FALLBACK)
# ═══════════════════════════════════════════════════════════════════════════

# Cac mau cau danh dau "giong phim X"
_SIMILAR_PATTERNS = [
    r"(?:giong\s+nhu\s+phim|giong\s+phim|giong\s+nhu|giong\s+voi|giong|tuong\s+tu\s+phim|tuong\s+tu\s+nhu|tuong\s+tu|kieu\s+nhu\s+phim|kieu\s+nhu|kieu\s+phim|nhu\s+phim|co\s+net\s+giong|like|similar\s+to|movies?\s+like)\s+[\"“'‘]?([a-zA-Z0-9\s:\-\',.&!]+?)[\"”'’]?(?:$|[,.!?;]|\s+(?:nhung|ma|va|hoac|khong|tranh|ung|voi|nhe|hon|tu\s+nam|thap\s+nien|duoi|cho\s+tre|cho\s+gia))",
]

# Cac mau cau phu dinh / tranh the loai
_AVOID_PATTERNS = [
    r"(?:tranh|khong\s+thich|khong\s+muon|khong\s+xem|bo\s+qua|bo\s+the\s+loai|bo|tru|ngoai\s+tru|ung\s+so|so\s+xem|ghét|ghet|avoid|no|not|without|except)\s+([^,.!?;]+)",
]

# Cac mau dieu chinh hoi thoai nhieu luot (multi-turn follow-up)
_FOLLOWUP_TRIGGERS = {
    "lighter": [
        "nhe hon", "nhe nhang hon", "bot cang thang", "bot nang ne", "tuoi sang hon",
        "vui hon", "bot buon", "bot u am", "de xem hon", "chill hon", "lighter", "less intense",
    ],
    "more_thrilling": [
        "hoi hop hon", "cang thang hon", "kich tinh hon", "gay can hon", "manh hon",
        "xoan nao hon", "den toi hon", "more thrilling", "more intense", "darker",
    ],
    "more_action": [
        "nhieu hanh dong hon", "danh nhau nhieu hon", "man nhan hon", "soi dong hon", "more action",
    ],
    "more_romance": [
        "lang man hon", "tinh cam hon", "ngot ngao hon", "more romantic",
    ],
    "newer": [
        "moi hon", "gan day hon", "phim moi", "nam gan day", "newer", "more recent",
    ],
    "older": [
        "cu hon", "kinh dien hon", "co dien", "xua hon", "older", "classic",
    ],
    "shorter": [
        "ngan hon", "ngan gon hon", "it thoi gian", "nhanh hon", "shorter",
    ],
}


def _match_movie_titles_in_text(
    text: str,
    folded_text: str,
    space: FeatureSpaceIndex,
) -> tuple[list[int], list[str], str]:
    """Tim ten phim trong cau yeu cau (ho tro ca cau truc 'giong phim X' va ten phim trong ngoac kep).
    Tra ve (movie_ids, movie_titles, remaining_folded_text)."""
    matched_ids: list[int] = []
    matched_titles: list[str] = []
    cleaned_folded = folded_text

    # 1. Tim trong ngoac kep truoc: "Inception", “Interstellar”, 'Avatar'
    quoted = re.findall(r'["“\'‘]([^"”\'’]{2,60})["”\'’]', text)
    candidates_raw = list(quoted)

    # 2. Tim theo mau "giong phim X", "tuong tu X", "nhu phim X", "like X"
    for pat in _SIMILAR_PATTERNS:
        for m in re.finditer(pat, folded_text):
            cand = m.group(1).strip()
            if len(cand) >= 2:
                candidates_raw.append(cand)

    # Doi chieu ung vien voi danh sach ten phim trong catalog
    for cand in candidates_raw:
        f_cand = _fold(cand).strip()
        # Bo cac tu thua o dau/cuoi nhu "phim", "bo phim", "movie"
        f_cand = re.sub(r"^(?:bo\s+phim|phim|movie|film)\s+", "", f_cand).strip()
        f_cand = re.sub(r"\s+(?:nhe|a|nha|di|voi|nua)$", "", f_cand).strip()
        if len(f_cand) < 2:
            continue

        best_mid = None
        best_title = None
        # Uu tien 1: Khop chinh xac toan bo ten phim
        for mid, title, f_title, _pop in space.titles_ordered:
            if f_title == f_cand:
                best_mid, best_title = mid, title
                break
        # Uu tien 2: Ten phim bat dau bang f_cand hoac f_cand bat dau bang ten phim (do dai >= 5)
        if best_mid is None and len(f_cand) >= 5:
            for mid, title, f_title, _pop in space.titles_ordered:
                if len(f_title) >= 5 and (
                    f_title.startswith(f_cand + ":")
                    or f_title.startswith(f_cand + " ")
                    or (len(f_title) >= 6 and f_cand.startswith(f_title + " "))
                ):
                    best_mid, best_title = mid, title
                    break

        if best_mid is not None and best_mid not in matched_ids:
            matched_ids.append(best_mid)
            matched_titles.append(best_title)
            cleaned_folded = cleaned_folded.replace(f_cand, " ")

    # 3. Neu nguoi dung viet "giong <Ten Phim>" ma regex tren bi dinh tu noi phia sau,
    # quet truc tiep cac ten phim >= 5 ky tu xuat hien ngay sau tu khoa "giong / tuong tu / nhu phim / like"
    if not matched_ids:
        sim_Cue = re.search(
            r"(?:giong\s+nhu\s+phim|giong\s+phim|giong\s+nhu|giong|tuong\s+tu\s+phim|tuong\s+tu|kieu\s+nhu|nhu\s+phim|like|similar\s+to)\s+(.+)",
            folded_text,
        )
        if sim_Cue:
            tail = sim_Cue.group(1)
            # Tim ten phim dai nhat va pho bien nhat xuat hien o dau tail
            best_match = None
            for mid, title, f_title, pop in space.titles_ordered:
                if len(f_title) < 3:
                    continue
                # Chi chap nhan khop tu ranh gioi tu (word boundary)
                if re.search(rf"(?:^|\b){re.escape(f_title)}(?:\b|$)", tail):
                    # Tranh khop nham cac tu tieng Anh thong dung nhu "up", "her", "it" neu khong viet hoa
                    if f_title in {"up", "her", "it", "us", "life", "love", "home", "war", "time"}:
                        if title not in text:
                            continue
                    score = (len(f_title.split()), pop)
                    if best_match is None or score > best_match[0]:
                        best_match = (score, mid, title, f_title)
            if best_match is not None:
                _, mid, title, f_title = best_match
                matched_ids.append(mid)
                matched_titles.append(title)
                cleaned_folded = cleaned_folded.replace(f_title, " ")

    return matched_ids, matched_titles, cleaned_folded


def _extract_genres_from_segment(segment_folded: str, return_matched_phrases: bool = False):
    """Tim danh sach the loai xuat hien trong mot doan van ban da bo dau."""
    found: list[str] = []
    matched_phrases: list[str] = []
    # Loai bo cac cum tu so luong/thu tu "hai nguoi", "hai anh em", "hai chi em", "hai the gioi", "thu hai"...
    seg_clean = re.sub(
        r"\b(?:hai\s+(?:nguoi|anh\s+em|chi\s+em|vo\s+chong|ban|cha\s+con|me\s+con|the\s+gioi|quoc\s+gia|phe|bang\s+dang|ca\s+the)|thu\s+hai)\b",
        " ",
        segment_folded,
    )
    for genre, phrases in GENRE_SYNONYMS.items():
        for p in sorted(phrases, key=len, reverse=True):
            fp = _fold(p)
            if re.search(rf"(?:^|\b){re.escape(fp)}(?:\b|$)", seg_clean):
                if genre not in found:
                    found.append(genre)
                matched_phrases.append(fp)
    if return_matched_phrases:
        return found, matched_phrases
    return found


def is_gibberish(text: str) -> bool:
    """Kiem tra chuoi ky tu vo nghia / go linh tinh (VD: 'dddd', 'aaaaa', '???', '123456')."""
    s = (text or "").strip()
    if not s:
        return True
    if not re.search(r"[a-zA-ZÀ-ỹà-ỹ]", s):
        return True
    if re.search(r"^(.)\1{2,}$", s, flags=re.IGNORECASE):
        return True
    if len(s.split()) == 1 and re.search(r"(.)\1{3,}", s, flags=re.IGNORECASE):
        return True
    return False


def parse_intent_local(
    message: str,
    space: FeatureSpaceIndex,
    previous_intent: Optional[ChatIntent] = None,
) -> ChatIntent:
    """Cach 1 (Cuc bo): Phan tich cau nhap cua nguoi dung bang tu dien + quy tac + khop catalog.
    Ho tro day du ca cau don va hoi thoai nhieu luot (multi-turn refinement)."""
    raw = (message or "").strip()
    if is_gibberish(raw):
        return ChatIntent(parser_source="local")
    folded = _fold(raw)
    intent = ChatIntent(parser_source="local")

    # 1. Nhan dien "giong phim X" truoc de loai ten phim khoi phan tich the loai
    sim_ids, sim_titles, folded_no_title = _match_movie_titles_in_text(raw, folded, space)
    intent.similar_movie_ids = sim_ids
    intent.similar_movie_titles = sim_titles

    # 2. Tach phan phu dinh ("tranh kinh di", "khong thich mau me, chien tranh", "bo hanh dong")
    avoid_genres: list[str] = []
    positive_folded = folded_no_title
    for pat in _AVOID_PATTERNS:
        for m in re.finditer(pat, folded_no_title):
            seg = m.group(1)
            # Neu trong mệnh đề tránh có từ nối sang vế muốn ("tránh kinh dị nhưng thích hài")
            seg_cut = re.split(r"\b(?:nhung|ma\s+thich|thich|muon|uu\s+tien|chon)\b", seg)[0]
            g_avoid = _extract_genres_from_segment(seg_cut)
            for g in g_avoid:
                if g not in avoid_genres:
                    avoid_genres.append(g)
            # Kiem tra xem nguoi dung co noi "tranh buon / tranh cang thang" khong
            if any(w in seg_cut for w in ("buon", "bi kich", "nang ne")):
                if "Drama" not in avoid_genres:
                    avoid_genres.append("Drama")
            if any(w in seg_cut for w in ("cang thang", "hoi hop", "bao luc", "mau me")):
                for g in ("Horror", "Thriller", "Crime"):
                    if g not in avoid_genres:
                        avoid_genres.append(g)
            positive_folded = positive_folded.replace(seg_cut, " ")

    intent.avoid_genres = avoid_genres

    # 3. Nhan dien Tam trang (Mood) tren phan tich cuc
    wanted_genres: list[str] = []
    mood_labels: list[str] = []
    en_kw_parts: list[str] = []
    matched_mood_or_genre_phrases: list[str] = []

    for mood in MOOD_DICTIONARY:
        matched_any_trig = False
        for trig in sorted(mood["triggers"], key=len, reverse=True):
            f_trig = _fold(trig)
            if re.search(rf"(?:^|\b){re.escape(f_trig)}(?:\b|$)", positive_folded):
                if not matched_any_trig:
                    if mood["label"] not in mood_labels:
                        mood_labels.append(mood["label"])
                    for g in mood["genres"]:
                        if g not in wanted_genres and g not in avoid_genres:
                            wanted_genres.append(g)
                    for g in mood["avoid"]:
                        if g not in avoid_genres and g not in wanted_genres:
                            avoid_genres.append(g)
                    en_kw_parts.append(mood["en_keywords"])
                    matched_any_trig = True
                matched_mood_or_genre_phrases.append(f_trig)

    # 4. Nhan dien The loai truc tiep tren phan tich cuc (dat len dau danh sach uu tien)
    explicit_genres, matched_genre_phrases = _extract_genres_from_segment(
        positive_folded, return_matched_phrases=True
    )
    matched_mood_or_genre_phrases.extend(matched_genre_phrases)
    for g in reversed(explicit_genres):
        if g in avoid_genres:
            avoid_genres.remove(g)  # Neu nguoi dung noi ro "muon xem X", uu tien X
        if g in wanted_genres:
            wanted_genres.remove(g)
        wanted_genres.insert(0, g)

    intent.wanted_genres = wanted_genres
    intent.mood_labels = mood_labels

    # 4.5. Nhan dien Yeu cau theo Do tuoi (Duoi 18 tuoi vs Tren 18 tuoi / 18+)
    _UNDER_18_RE = re.compile(
        r"\b(?:duoi\s+18\s+tuoi|duoi\s+18t?|< ?18|under\s+18|cho\s+tre\s+em|cho\s+thieu\s+nhi|cho\s+tre\s+con|cho\s+hoc\s+sinh|tuoi\s+teen|thanh\s+thieu\s+nien|for\s+kids|for\s+children|tre\s+nho|hoc\s+sinh)\b"
    )
    _OVER_18_RE = re.compile(
        r"(?:\b(?:tren\s+18\s+tuoi|tren\s+18t?|> ?18|over\s+18|18\s*plus|18\s*cong|cho\s+nguoi\s+lon|danh\s+cho\s+nguoi\s+lon|nguoi\s+lon|adult)\b|18\s*\+)"
    )

    is_under_18 = bool(_UNDER_18_RE.search(positive_folded))
    is_over_18 = bool(_OVER_18_RE.search(positive_folded))

    if is_under_18 and not is_over_18:
        for g in ("Family", "Animation", "Adventure", "Comedy"):
            if g not in wanted_genres and g not in avoid_genres:
                wanted_genres.append(g)
        for g in ("Horror", "War"):
            if g not in avoid_genres and g not in explicit_genres:
                avoid_genres.append(g)
        if "dưới 18 tuổi" not in mood_labels:
            mood_labels.append("dưới 18 tuổi")
        en_kw_parts.append("family friendly kids children animation adventure youth school")
        positive_folded = _UNDER_18_RE.sub(" ", positive_folded)
        folded_no_title = _UNDER_18_RE.sub(" ", folded_no_title)

    elif is_over_18 and not is_under_18:
        # Neu chua neu ro the loai cu the, mac dinh uu tien: Lang man, Hanh dong, Kinh di, Giat gan
        if not explicit_genres:
            for g in ("Romance", "Action", "Horror", "Thriller"):
                if g not in wanted_genres and g not in avoid_genres:
                    wanted_genres.append(g)
        else:
            # Da co the loai cu the (VD: "phim ma 18+" hoac "phim tinh cam 18+")
            # -> giu nguyen the loai nguoi dung muon o vi tri so 1, chi bo sung the loai ho tro tuong thich
            if "Romance" in explicit_genres:
                if "Drama" not in wanted_genres and "Drama" not in avoid_genres:
                    wanted_genres.append("Drama")
            elif "Horror" in explicit_genres:
                if "Thriller" not in wanted_genres and "Thriller" not in avoid_genres:
                    wanted_genres.append("Thriller")
            elif "Action" in explicit_genres:
                if "Thriller" not in wanted_genres and "Thriller" not in avoid_genres:
                    wanted_genres.append("Thriller")
        for g in ("Family", "Animation"):
            if g not in avoid_genres and g not in explicit_genres:
                avoid_genres.append(g)
        if "dành cho 18+" not in mood_labels:
            mood_labels.append("dành cho 18+")
        en_kw_parts.append("mature romance love passion action thrilling suspense horror scary adult")
        positive_folded = _OVER_18_RE.sub(" ", positive_folded)
        folded_no_title = _OVER_18_RE.sub(" ", folded_no_title)

    intent.wanted_genres = wanted_genres
    intent.avoid_genres = avoid_genres
    intent.mood_labels = mood_labels

    # 5. Nhan dien Dao dien / Dien vien trong top 50/200 (lam truoc nam phat hanh de tranh nham "co dien" = classic)
    for f_dir, orig_dir, _col in space.directors_folded:
        if len(f_dir) >= 5 and re.search(rf"(?:^|\b){re.escape(f_dir)}(?:\b|$)", folded):
            intent.director = orig_dir
            positive_folded = positive_folded.replace(f_dir, " ")
            folded_no_title = folded_no_title.replace(f_dir, " ")
            break
    for f_act, orig_act, _col in space.actors_folded:
        if len(f_act) >= 5 and re.search(rf"(?:^|\b){re.escape(f_act)}(?:\b|$)", folded):
            intent.actor = orig_act
            positive_folded = positive_folded.replace(f_act, " ")
            folded_no_title = folded_no_title.replace(f_act, " ")
            break

    # 6. Nhan dien Thoi ky / Nam phat hanh (VD: "thap nien 90", "2010s", "tu 2010 den 2020", "sau 2015", "truoc 2000")
    m_range = re.search(r"(?:tu\s+nam\s+|tu\s+|nam\s+|giai\s+doan\s+)?(19\d{2}|20\d{2})\s*(?:den|-|–|toi|to)\s*(19\d{2}|20\d{2})", folded)
    if m_range:
        y1, y2 = int(m_range.group(1)), int(m_range.group(2))
        intent.year_from, intent.year_to = min(y1, y2), max(y1, y2)
    else:
        m_decade_vi = re.search(r"thap\s+nien\s+(19\d0|20\d0|\d0)s?", folded)
        m_decade_en = re.search(r"\b(19\d0|20\d0)s\b|\b([789]0)s\b", folded)
        if m_decade_vi:
            dec = int(m_decade_vi.group(1))
            if dec < 100:
                dec = 1900 + dec if dec >= 50 else 2000 + dec
            intent.year_from, intent.year_to = dec, dec + 9
        elif m_decade_en:
            raw_d = m_decade_en.group(1) or m_decade_en.group(2)
            dec = int(raw_d)
            if dec < 100:
                dec = 1900 + dec
            intent.year_from, intent.year_to = dec, dec + 9
        else:
            m_from = re.search(r"(?:tu\s+nam|sau\s+nam|tu|sau|from|after|since)\s+(19\d{2}|20\d{2})", folded)
            m_to = re.search(r"(?:truoc\s+nam|truoc|den\s+nam|before|until)\s+(19\d{2}|20\d{2})", folded)
            m_exact = re.search(r"\bnam\s+(19\d{2}|20\d{2})\b", folded)
            if m_from:
                intent.year_from = int(m_from.group(1))
            if m_to:
                intent.year_to = int(m_to.group(1))
            if m_exact and not m_from and not m_to:
                y = int(m_exact.group(1))
                intent.year_from, intent.year_to = y, y
            if not m_from and not m_to and not m_exact:
                if re.search(r"\b(?:phim\s+moi|gan\s+day|moi\s+nhat|hien\s+dai)\b", folded):
                    intent.year_from = 2010
                elif re.search(r"\b(?:kinh\s+dien|phim\s+co\s+dien|phim\s+xua|classic)\b", folded):
                    intent.year_to = 2002

    # 7. Nhan dien Thoi luong (VD: "duoi 100 phut", "ngan", "khoang 2 tieng")
    m_min = re.search(r"(?:duoi|it\s+hon|khong\s+qua|toi\s+da|under|<)\s*(\d{2,3})\s*(?:phut|p|min)", folded)
    if m_min:
        intent.max_runtime = int(m_min.group(1))
    elif re.search(r"\b(?:phim\s+ngan|ngan\s+gon|it\s+thoi\s+gian|duoi\s+1\s+tieng\s+ruoi)\b", folded):
        intent.max_runtime = 100
    elif re.search(r"\b(?:khoang\s+2\s+tieng|khoang\s+2\s+gio|duoi\s+2\s+tieng)\b", folded):
        intent.max_runtime = 125
    # 7.5. Nhan dien TMDB Keywords (VD: "marvel", "superhero", "breaking the fourth wall", "zombie", "time travel"...)
    # Tao ban sao cua positive_folded da loai bo cac cum tu the loai/tam trang thong thuong de tranh khop nham "hai" -> "hai Jaan", "khoa hoc vien tuong" -> keyword rac
    content_folded = positive_folded
    for mp in matched_mood_or_genre_phrases:
        # Giu lai cac cum tu chu de cu the (zombie, sieu anh hung, du hanh thoi gian, xac song, vo thuat...)
        if mp not in VI_TO_EN_TOPIC_KEYWORDS:
            content_folded = re.sub(rf"(?:^|\b){re.escape(mp)}(?:\b|$)", " ", content_folded)
    # Xoa cac tu chi quan he nhu "giong phim", "kieu nhu", "dao dien", "dien vien", "tu nam", "thap nien"
    content_folded = re.sub(
        r"\b(?:giong\s+nhu\s+phim|giong\s+phim|giong\s+nhu|giong|tuong\s+tu|kieu\s+nhu|nhu\s+phim|dao\s+dien|dien\s+vien|thap\s+nien|tu\s+nam|truoc\s+nam|sau\s+nam|duoi\s+\d+\s+phut)\b",
        " ",
        content_folded,
    )

    # 8.1. Nhan dien Cum tu Chu de & Noi dung Tieng Viet (VI_TO_EN_TOPIC_KEYWORDS) TRUOC
    # de tranh cac am tiet tieng Viet ("vien", "tien", "duong", "hanh"...) bi khop nham vao TMDB English Keywords
    matched_topics_vi: list[str] = []
    topic_en_terms: list[str] = []
    matched_kws: list[str] = []
    kw_display = ""
    remaining_for_words = content_folded

    for vi_phrase, en_expansion in sorted(VI_TO_EN_TOPIC_KEYWORDS.items(), key=lambda x: -len(x[0])):
        f_vi = _fold(vi_phrase)
        if re.search(rf"(?:^|\b){re.escape(f_vi)}(?:\b|$)", remaining_for_words):
            en_kw_parts.append(en_expansion)
            topic_en_terms.append(en_expansion)
            matched_topics_vi.append(vi_phrase.strip())
            remaining_for_words = re.sub(rf"(?:^|\b){re.escape(f_vi)}(?:\b|$)", " ", remaining_for_words)
            # Anh xa tu dau tien (chinh xac nhat) cua en_expansion sang TMDB keywords neu co
            primary_en = en_expansion.split()[0].lower() if en_expansion.split() else ""
            if len(primary_en) >= 4 and primary_en in getattr(space, "keyword_to_mids", {}):
                if primary_en not in matched_kws:
                    matched_kws.append(primary_en)

    # 8.2. Nhan dien TMDB Keywords tieng Anh (VD: "marvel", "superhero", "breaking the fourth wall", "time travel"...)
    for f_kw, orig_kw, _mids in getattr(space, "keywords_folded", []):
        if len(f_kw) >= 4 and not f_kw.isdigit() and re.search(r"\b" + re.escape(f_kw) + r"\b", remaining_for_words):
            # Neu keyword la 1 tu don va nam trong danh sach am tiet tieng Viet (_VI_FALSE_EN hoac VI_WORD_TO_EN) thi bo qua
            if " " not in f_kw and (f_kw in _VI_FALSE_EN or f_kw in VI_WORD_TO_EN):
                continue
            if orig_kw not in matched_kws:
                matched_kws.append(orig_kw)
            if not kw_display:
                kw_display = orig_kw
            remaining_for_words = remaining_for_words.replace(f_kw, " ")
            if len(matched_kws) >= 4:
                break

    # Khop tu don dac trung trong keywords (VD: "marvel" -> "marvel comic", "marvel cinematic universe")
    if not matched_kws and getattr(space, "keywords_folded", None):
        _KW_STOP_WORDS = {
            "phim", "xem", "muon", "thich", "nhung", "cho", "minh", "mot", "cac", "nhu",
            "the", "loai", "gi", "ve", "movie", "movies", "film", "films", "like", "with",
            "want", "watch", "some", "good", "best", "about", "from", "into", "hay",
            "nguoi", "chuyen", "cuoc", "trong", "cung", "nhau", "duoc", "biet", "cong", "vien",
        }
        _SHORT_KW_ALIASES = {
            "dc": ["dc comics", "dc extended universe"],
            "mcu": ["marvel cinematic universe", "marvel comic"],
            "007": ["spy", "secret agent", "mi6"],
        }
        for short_alias, alias_kws in _SHORT_KW_ALIASES.items():
            if re.search(r"\b" + re.escape(short_alias) + r"\b", remaining_for_words):
                matched_kws.extend(alias_kws)
                kw_display = short_alias.upper()
                break

        if not matched_kws:
            tokens = [
                t for t in re.findall(r"[a-zA-Z]+", remaining_for_words)
                if len(t) >= 4 and t not in _KW_STOP_WORDS and t not in _VI_FALSE_EN and t not in VI_WORD_TO_EN
            ]
            for tok in tokens:
                hits = []
                for f_kw, orig_kw, mids in space.keywords_folded:
                    if re.search(r"\b" + re.escape(tok) + r"\b", f_kw):
                        hits.append((orig_kw, len(mids)))
                if hits:
                    hits.sort(key=lambda h: -h[1])
                    matched_kws.extend([h[0] for h in hits[:5]])
                    kw_display = tok
                    remaining_for_words = remaining_for_words.replace(tok, " ")
                    break

    if matched_kws:
        intent.matched_keywords = matched_kws
        if not kw_display and not matched_topics_vi:
            kw_display = matched_kws[0]
        intent.matched_keyword_display = kw_display or (", ".join(matched_topics_vi[:4]) if matched_topics_vi else "")
        intent.keywords_en = (intent.keywords_en + " " + " ".join(matched_kws)).strip()
        if not intent.keywords_raw:
            intent.keywords_raw = intent.matched_keyword_display

    # 8.2. Phan tich tu don tieng Viet (Word-level fallback) tren phan van ban CON LAI (chua bi match boi genre/mood/topic)
    # VD: "mot nguoi dan ong bi mac ket tren hoang dao phai tim cach song sot"
    _VI_STOP_CONTENT = {
        "phim", "bo", "xem", "muon", "thich", "nhung", "cho", "minh", "mot", "cac", "nhu",
        "the", "loai", "gi", "ve", "co", "la", "va", "hoac", "nhung", "ma", "thi", "bi",
        "duoc", "cua", "trong", "ngoai", "tren", "duoi", "truoc", "sau", "nay", "kia",
        "rat", "qua", "lam", "hon", "nhat", "nua", "di", "nhe", "nha", "voi", "cung",
        "nguoi", "dan", "ong", "ba", "co", "chu", "anh", "chi", "em", "ho", "chung",
        "ke", "chuyen", "noi", "dung", "xoay", "quanh", "cuoc", "doi", "hanh", "trinh",
        "tim", "kiem", "goi", "y", "hay", "tot", "moi", "cu", "nam", "phut", "tieng",
        "thoi", "tiet", "hom", "ban", "ghe", "tu", "lanh", "nha", "cuoi", "tuan", "gio",
        "nghi", "trua", "nhanh", "de", "xem", "bom", "tan", "gay", "can", "hao", "hung",
    }
    folded_words = re.findall(r"[a-z]+", remaining_for_words)
    word_level_en: list[str] = []
    word_level_vi: list[str] = []
    for w in folded_words:
        if w in _VI_STOP_CONTENT or len(w) < 2:
            continue
        if w in VI_WORD_TO_EN:
            word_level_en.append(VI_WORD_TO_EN[w])
            word_level_vi.append(w)

    # Lay them cac tu tieng Anh co trong vocab cua Rich TF-IDF hoac Overview TF-IDF
    vocab_rich = getattr(space, "rich_tfidf_en", space.tfidf).vocabulary_
    raw_tokens = re.findall(r"[a-zA-Z]{4,}", remaining_for_words)
    en_direct = [tok for tok in raw_tokens if tok in vocab_rich and tok not in _VI_FALSE_EN]
    if en_direct:
        en_kw_parts.append(" ".join(en_direct))
        topic_en_terms.append(" ".join(en_direct))

    # Chi kich hoat word-level fallback khi nguoi dung nhap mo ta noi dung (>= 2 tu don dac trung)
    if len(word_level_en) >= 2:
        en_kw_parts.append(" ".join(word_level_en))
        topic_en_terms.append(" ".join(word_level_en))

    if matched_topics_vi:
        intent.keywords_raw = ", ".join(matched_topics_vi[:4])
        if not intent.matched_keyword_display:
            intent.matched_keyword_display = ", ".join(matched_topics_vi[:4])
    elif en_direct:
        intent.keywords_raw = " ".join(en_direct[:4])
    elif len(word_level_vi) >= 2:
        intent.keywords_raw = " ".join(word_level_vi[:5])

    intent.keywords_en = " ".join(en_kw_parts).strip()
    intent.content_query_en = " ".join(topic_en_terms).strip()
    if matched_topics_vi or en_direct or len(word_level_vi) >= 2:
        # Luu cau truy van tieng Viet da loc tu dung de so khop truc tiep voi overview_vi
        content_vi_tokens = [w for w in re.findall(r"[a-z]+", content_folded) if w not in _VI_STOP_CONTENT and len(w) >= 2]
        intent.content_query_vi = " ".join(content_vi_tokens)

    # 9. Xu ly hoi thoai nhieu luot (Multi-turn refinement: "cho minh cai nhe hon nua", "bo kinh di", "them hai"...)
    if previous_intent is not None:
        detected_mod = False
        for mod_key, mod_phrases in _FOLLOWUP_TRIGGERS.items():
            if any(re.search(rf"(?:^|\b){re.escape(_fold(p))}(?:\b|$)", folded) for p in mod_phrases):
                detected_mod = True
                if mod_key == "lighter":
                    for g in ("Comedy", "Family", "Romance", "Animation"):
                        if g not in intent.wanted_genres:
                            intent.wanted_genres.append(g)
                    for g in ("Horror", "Thriller", "Crime", "War"):
                        if g not in intent.avoid_genres:
                            intent.avoid_genres.append(g)
                    if "nhẹ nhàng hơn" not in intent.mood_labels:
                        intent.mood_labels.append("nhẹ nhàng hơn")
                    intent.keywords_en = (intent.keywords_en + " lighthearted warm funny family").strip()
                elif mod_key == "more_thrilling":
                    for g in ("Thriller", "Mystery", "Crime"):
                        if g not in intent.wanted_genres:
                            intent.wanted_genres.insert(0, g)
                    if "kịch tính hơn" not in intent.mood_labels:
                        intent.mood_labels.append("kịch tính hơn")
                elif mod_key == "more_action":
                    for g in ("Action", "Adventure"):
                        if g not in intent.wanted_genres:
                            intent.wanted_genres.insert(0, g)
                elif mod_key == "more_romance":
                    if "Romance" not in intent.wanted_genres:
                        intent.wanted_genres.insert(0, "Romance")
                elif mod_key == "newer":
                    intent.year_from = max(intent.year_from or 2010, 2012)
                    intent.year_to = None
                elif mod_key == "older":
                    intent.year_to = min(intent.year_to or 2005, 2000)
                    intent.year_from = None
                elif mod_key == "shorter":
                    intent.max_runtime = min(intent.max_runtime or 100, 100)

        # Dau hieu cau ngan mang tinh bo sung/dieu chinh ("them...", "bo...", "doi sang...", "con phim nao...", "nua")
        is_short_refinement = bool(
            detected_mod
            or re.search(r"\b(?:hon\s+nua|hon|them|bo\s+bot|khong\s+co|doi\s+sang|con\s+phim|khac\s+di|nua\s+di)\b", folded)
            or (len(raw.split()) <= 6 and (intent.avoid_genres or intent.year_from or intent.max_runtime) and not intent.wanted_genres and not intent.similar_movie_ids)
        )

        if is_short_refinement:
            intent.is_followup = True
            # Ke thua cac rang buoc tu luot truoc neu luot nay khong ghi de
            for g in previous_intent.avoid_genres:
                if g not in intent.avoid_genres and g not in intent.wanted_genres:
                    intent.avoid_genres.append(g)
            for g in previous_intent.wanted_genres:
                if g not in intent.wanted_genres and g not in intent.avoid_genres:
                    intent.wanted_genres.append(g)
            if not intent.similar_movie_ids and previous_intent.similar_movie_ids:
                intent.similar_movie_ids = list(previous_intent.similar_movie_ids)
                intent.similar_movie_titles = list(previous_intent.similar_movie_titles)
            if intent.year_from is None and intent.year_to is None:
                intent.year_from = previous_intent.year_from
                intent.year_to = previous_intent.year_to
            if intent.max_runtime is None:
                intent.max_runtime = previous_intent.max_runtime
            if not intent.keywords_en and previous_intent.keywords_en:
                intent.keywords_en = previous_intent.keywords_en
            if not intent.keywords_raw and previous_intent.keywords_raw:
                intent.keywords_raw = previous_intent.keywords_raw

    return intent


def parse_intent_llm(
    message: str,
    space: FeatureSpaceIndex,
    previous_intent: Optional[ChatIntent] = None,
    timeout: float = 4.5,
) -> Optional[ChatIntent]:
    """Cach 2 (Tuy chon - LLM API): Goi Gemini API (GEMINI_API_KEY) hoac OpenAI-compatible API
    (OPENAI_API_KEY) de chuyen cau tu do tieng Viet sang JSON Intent.
    Neu khong co key hoac loi mang/timeout -> tra ve None de roi ve Cach 1 (Local)."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not gemini_key and not openai_key:
        return None

    valid_genres = space.genre_labels
    prev_json = json.dumps(previous_intent.to_dict(), ensure_ascii=False) if previous_intent else "null"
    system_prompt = (
        "Bạn là chuyên gia AI gợi ý và phân tích ý định tìm phim (Movie Intent & Plot Reasoner).\n"
        f"Danh sách thể loại hợp lệ duy nhất: {json.dumps(valid_genres)}.\n"
        "Hãy phân tích sâu câu yêu cầu của người dùng (kể cả khi họ mô tả cốt truyện mơ hồ, ẩn dụ, hoặc nhớ mang máng nội dung phim) "
        "và trả về DUY NHẤT một JSON object hợp lệ với các trường:\n"
        "{\n"
        '  "wanted_genres": [danh sách thể loại hợp lệ người dùng muốn],\n'
        '  "avoid_genres": [danh sách thể loại hợp lệ người dùng muốn tránh],\n'
        '  "mood_labels": [1-2 cụm từ ngắn tiếng Việt mô tả tâm trạng, ví dụ "nhẹ nhàng, thư giãn"],\n'
        '  "similar_movie_names": [tên phim cụ thể nếu người dùng nhắc tới "giống phim X"],\n'
        '  "ai_recommended_titles": [5 đến 8 tên phim tiếng Anh gốc (Original English Titles, phát hành từ 2017 trở về trước trong TMDB 5000) khớp sát nhất với cốt truyện/nội dung/yêu cầu người dùng mô tả],\n'
        '  "year_from": số nguyên hoặc null,\n'
        '  "year_to": số nguyên hoặc null,\n'
        '  "max_runtime": số phút tối đa hoặc null,\n'
        '  "director": tên đạo diễn (nếu có) hoặc null,\n'
        '  "actor": tên diễn viên (nếu có) hoặc null,\n'
        '  "keywords_raw": cụm từ chủ đề tiếng Việt ngắn gọn tóm tắt nội dung,\n'
        '  "keywords_en": 8-15 từ khóa tiếng Anh đặc trưng nhất mô tả cốt truyện, bối cảnh, nhân vật để tìm trên TF-IDF overview,\n'
        '  "is_followup": true nếu câu này tinh chỉnh lượt trước, ngược lại false\n'
        "}\n"
        f"Ý định lượt trước: {prev_json}\n"
        f"Câu người dùng: {message}"
    )

    try:
        raw_json_text = None
        if gemini_key:
            model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": system_prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_json_text = data["candidates"][0]["content"]["parts"][0]["text"]
        elif openai_key:
            base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": system_prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            }
            req = urllib.request.Request(
                f"{base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_json_text = data["choices"][0]["message"]["content"]

        if not raw_json_text:
            return None

        cleaned = re.sub(r"^```(?:json)?|```$", "", raw_json_text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)

        # Ket hop ket qua LLM voi bộ khớp tên phim cục bộ trong catalog
        local_fallback = parse_intent_local(message, space, previous_intent)
        intent = ChatIntent(parser_source="llm")
        intent.wanted_genres = [g for g in parsed.get("wanted_genres", []) if g in valid_genres]
        intent.avoid_genres = [
            g for g in parsed.get("avoid_genres", [])
            if g in valid_genres and g not in intent.wanted_genres
        ]
        intent.mood_labels = [str(x) for x in parsed.get("mood_labels", []) if x][:3]

        # Khop ten phim tu similar_movie_names cua LLM + local matcher
        sim_ids = list(local_fallback.similar_movie_ids)
        sim_titles = list(local_fallback.similar_movie_titles)
        for name in parsed.get("similar_movie_names", []) or []:
            ids_m, titles_m, _ = _match_movie_titles_in_text(f'"{name}"', _fold(f'"{name}"'), space)
            for mid, mtitle in zip(ids_m, titles_m):
                if mid not in sim_ids:
                    sim_ids.append(mid)
                    sim_titles.append(mtitle)
        intent.similar_movie_ids = sim_ids
        intent.similar_movie_titles = sim_titles

        # Khop danh sach phim do AI suy luan truc tiep tu cot truyen (ai_recommended_titles)
        ai_ids: list[int] = []
        ai_titles: list[str] = []
        for name in parsed.get("ai_recommended_titles", []) or []:
            ids_m, titles_m, _ = _match_movie_titles_in_text(f'"{name}"', _fold(f'"{name}"'), space)
            for mid, mtitle in zip(ids_m, titles_m):
                if mid not in ai_ids and mid not in sim_ids:
                    ai_ids.append(mid)
                    ai_titles.append(mtitle)
        intent.ai_candidate_ids = ai_ids
        intent.ai_candidate_titles = ai_titles

        intent.year_from = parsed.get("year_from") or local_fallback.year_from
        intent.year_to = parsed.get("year_to") or local_fallback.year_to
        intent.max_runtime = parsed.get("max_runtime") or local_fallback.max_runtime
        intent.director = local_fallback.director or parsed.get("director")
        intent.actor = local_fallback.actor or parsed.get("actor")
        intent.keywords_raw = str(parsed.get("keywords_raw") or local_fallback.keywords_raw or "").strip()
        llm_kw_en = str(parsed.get("keywords_en") or "").strip()
        intent.keywords_en = f"{llm_kw_en} {local_fallback.keywords_en}".strip()
        intent.content_query_en = f"{llm_kw_en} {local_fallback.content_query_en}".strip()
        intent.content_query_vi = local_fallback.content_query_vi

        # Anh xa cac tu khoa tieng Anh do LLM sinh ra sang TMDB keywords trong DB
        matched_kws = list(local_fallback.matched_keywords)
        for en_w in re.findall(r"[a-zA-Z]{4,}", llm_kw_en.lower()):
            if en_w in getattr(space, "keyword_to_mids", {}) and en_w not in matched_kws and len(matched_kws) < 10:
                matched_kws.append(en_w)
        intent.matched_keywords = matched_kws
        intent.matched_keyword_display = local_fallback.matched_keyword_display or intent.keywords_raw
        intent.is_followup = bool(parsed.get("is_followup") or local_fallback.is_followup)
        return intent
    except Exception:
        return None


def parse_user_query(
    message: str,
    db_path: str = DEFAULT_DB_PATH,
    previous_intent: Optional[ChatIntent] = None,
    use_llm: bool = True,
) -> ChatIntent:
    """Ham dieu phoi Hieu yeu cau: thu LLM neu co key & duoc bat, loi hoac khong co key thi dung Local."""
    if is_gibberish(message):
        return ChatIntent(parser_source="local")
    space = get_feature_space(db_path)
    if use_llm:
        llm_intent = parse_intent_llm(message, space, previous_intent=previous_intent)
        if llm_intent is not None:
            return llm_intent
    return parse_intent_local(message, space, previous_intent=previous_intent)


# ═══════════════════════════════════════════════════════════════════════════
# 5. DUNG QUERY VECTOR TRONG KHONG GIAN 324 CHIEU
# ═══════════════════════════════════════════════════════════════════════════

def build_query_vector(
    intent: ChatIntent,
    space: FeatureSpaceIndex,
) -> np.ndarray:
    """Dung Query Vector 324 chieu trong cung khong gian dac trung cua nhom:
      - [0:20]    Genre multi-hot
      - [20:71]   Director one-hot
      - [71:271]  Cast multi-hot
      - [271:321] Overview TF-IDF -> SVD 50 chieu
      - [321:324] Numeric: [vote_average, popularity, release_year] scaled [0, 1]
    Neu co 'giong phim X', ket hop vector 324 chieu cua phim X voi tin hieu the loai/tu khoa."""
    q = np.zeros(324, dtype=np.float32)

    # 1. Genres [0:20]
    wanted = list(intent.wanted_genres)
    # Neu nguoi dung chi noi "giong phim X" ma chua neu the loai, lay the loai cua phim X (tru the loai bi tranh)
    if not wanted and intent.similar_movie_ids:
        for mid in intent.similar_movie_ids:
            meta = space.movies.get(mid)
            if meta:
                for g in meta["genres"]:
                    if g not in intent.avoid_genres and g not in wanted:
                        wanted.append(g)

    for g in wanted:
        col = space.genre_to_col.get(g)
        if col is not None:
            q[col] = 1.0

    # 2. Director [20:71]
    if intent.director and intent.director in space.director_to_col:
        q[space.director_to_col[intent.director]] = 1.0
    else:
        # Mac dinh cot Other/Unknown (col 70) bang 0.5 de khong lam lech dot product voi 90% phim
        q[70] = 0.5

    # 3. Cast [71:271]
    if intent.actor and intent.actor in space.cast_to_col:
        q[space.cast_to_col[intent.actor]] = 1.0

    # 4. Overview SVD [271:321]
    if intent.keywords_en:
        svd_vec = space.project_text_to_svd(intent.keywords_en)
        # Neu nguoi dung mo ta noi dung phim cu the (content_query_en) ma khong neu the loai,
        # tang do lon vector SVD len 1.0 de tin hieu noi dung chiem uu the trong 324 chieu
        target_svd_norm = 1.0 if (intent.content_query_en and not intent.wanted_genres) else 0.50
        norm = float(np.linalg.norm(svd_vec))
        if norm > 0:
            svd_vec = svd_vec * (target_svd_norm / norm)
        q[271:321] = svd_vec

    # 5. Numeric [321:324]: vote_average (321), popularity (322), release_year (323)
    q[321] = 0.78  # Uu tien phim diem kha cao
    q[322] = 0.35  # Do pho bien vua phai
    if intent.year_from or intent.year_to:
        y_from = intent.year_from or space.min_year
        y_to = intent.year_to or space.max_year
        target_year = 0.5 * (y_from + y_to)
        span = max(1, space.max_year - space.min_year)
        q[323] = float(np.clip((target_year - space.min_year) / span, 0.0, 1.0))
    else:
        q[323] = 0.82  # Mac dinh nghieng nhe ve phim hien dai (~2000s-2010s)

    # 6. Neu co "giong phim X": lay trung binh vector 324 chieu that cua phim X trong DB
    if intent.similar_movie_ids:
        sim_vecs = []
        for mid in intent.similar_movie_ids:
            row_idx = space.id_to_row.get(mid)
            if row_idx is not None:
                sim_vecs.append(space.matrix[row_idx].copy())
        if sim_vecs:
            seed_vec = np.mean(np.vstack(sim_vecs), axis=0).astype(np.float32)
            # Xoa tin hieu o cac the loai ma nguoi dung muon tranh
            for g in intent.avoid_genres:
                col = space.genre_to_col.get(g)
                if col is not None:
                    seed_vec[col] = 0.0
            # Neu nguoi dung co chi dinh them the loai/tam trang rieng (VD: "giong Inception nhung nhe nhang hon")
            if intent.wanted_genres or intent.keywords_en:
                q = 0.60 * seed_vec + 0.40 * q
            else:
                q = seed_vec

    # Dam bao cac the loai bi tranh luon bang 0 trong query vector
    for g in intent.avoid_genres:
        col = space.genre_to_col.get(g)
        if col is not None:
            q[col] = 0.0

    return q


# ═══════════════════════════════════════════════════════════════════════════
# 6. TIM KIEM, TRON PROFILE & RANKING + SINH LY DO
# ═══════════════════════════════════════════════════════════════════════════

def _build_reason(
    meta: dict[str, Any],
    intent: ChatIntent,
    query_cos: float,
    profile_cos: Optional[float],
    runtime: Optional[int],
    liked_genres: set[str],
    matched_kw_label: Optional[str] = None,
) -> str:
    """Sinh ly do goi y cu the, trung thuc cho tung phim."""
    reasons: list[str] = []
    m_genres = meta.get("genres", [])

    # 0. Neu AI (LLM) suy luan truc tiep bo phim nay tu cot truyen
    if meta.get("movie_id") in intent.ai_candidate_ids:
        reasons.append("AI đề xuất khớp cốt truyện")
    elif matched_kw_label:
        reasons.append(f"Từ khóa: {matched_kw_label}")
    elif intent.keywords_raw and query_cos > 0.35:
        reasons.append(f"Nội dung khớp chủ đề “{intent.keywords_raw}”")

    # 1. Neu khop "giong phim X"
    if intent.similar_movie_titles and query_cos > 0.35:
        reasons.append(f"Nội dung gần với {', '.join(intent.similar_movie_titles[:2])}")

    # 2. The loai khop voi y dinh
    matched_wanted = [GENRE_VI_LABELS.get(g, g) for g in intent.wanted_genres if g in m_genres]
    if matched_wanted:
        reasons.append(f"Đúng chất {', '.join(matched_wanted[:2])}")
    elif intent.mood_labels:
        reasons.append(f"Hợp tâm trạng {intent.mood_labels[0]}")

    # 3. Dao dien / Dien vien / Nam / Thoi luong neu nguoi dung yeu cau
    if intent.director and meta.get("director") == intent.director:
        reasons.append(f"Đạo diễn {intent.director}")
    if intent.actor and intent.actor in (meta.get("cast") or []):
        reasons.append(f"Có {intent.actor}")
    if (intent.year_from or intent.year_to) and meta.get("release_year"):
        reasons.append(f"Phát hành năm {meta['release_year']}")
    if intent.max_runtime and runtime:
        reasons.append(f"{runtime} phút")

    # 4. Lien he voi Profile ca nhan cua nguoi dung
    if profile_cos is not None and profile_cos > 0.45:
        overlap_gu = [GENRE_VI_LABELS.get(g, g) for g in m_genres if g in liked_genres]
        if overlap_gu:
            reasons.append(f"hợp gu {', '.join(overlap_gu[:2])} của bạn")
        else:
            reasons.append("hợp hồ sơ sở thích của bạn")
    elif not reasons:
        if (meta.get("vote_average") or 0) >= 7.5:
            reasons.append(f"Được đánh giá cao ({meta['vote_average']:.1f}★)")
        else:
            reasons.append("Được nhiều khán giả yêu thích")

    return " · ".join(reasons[:3])


def chat_recommend(
    user_id: str,
    message: str = "",
    *,
    db_path: str = DEFAULT_DB_PATH,
    previous_intent: Optional[ChatIntent | dict] = None,
    intent_override: Optional[dict] = None,
    exclude_ids: Optional[set[int]] = None,
    runtimes: Optional[dict[int, Optional[int]]] = None,
    top_n: int = 10,
    candidate_k: int = 120,
    query_weight: float = 0.75,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Luong chinh cua Chat Bot goi y phim:
      1. Hieu yeu cau -> ChatIntent (hoac nhan intent_override khi nguoi dung bam sua tag tren UI)
      2. Dung Query Vector 324 chieu
      3. Loc phim bi loai (the loai tranh, phim da tuong tac, chinh phim X, nam, thoi luong)
      4. Tinh Cosine Similarity voi Query Vector va TRON voi User Profile (neu co)
      5. Dua qua Multi-Objective Ranking (Cosine 0.6 + Rating 0.2 + Popularity 0.1 + Newness 0.1) + Online Reranker
      6. Tra ve danh sach phim THAT trong catalog + ly do + dong 'Minh hieu ban muon: ...'"""
    space = get_feature_space(db_path)

    prev_obj: Optional[ChatIntent] = None
    if isinstance(previous_intent, ChatIntent):
        prev_obj = previous_intent
    elif isinstance(previous_intent, dict) and previous_intent:
        prev_obj = ChatIntent(
            wanted_genres=list(previous_intent.get("wanted_genres") or []),
            avoid_genres=list(previous_intent.get("avoid_genres") or []),
            mood_labels=list(previous_intent.get("mood_labels") or []),
            similar_movie_ids=[
                int(m["movie_id"]) if isinstance(m, dict) else int(m)
                for m in (previous_intent.get("similar_movies") or previous_intent.get("similar_movie_ids") or [])
            ],
            similar_movie_titles=[
                str(m["title"]) if isinstance(m, dict) else str(m)
                for m in (previous_intent.get("similar_movies") or previous_intent.get("similar_movie_titles") or [])
            ],
            year_from=previous_intent.get("year_from"),
            year_to=previous_intent.get("year_to"),
            max_runtime=previous_intent.get("max_runtime"),
            director=previous_intent.get("director"),
            actor=previous_intent.get("actor"),
            keywords_raw=str(previous_intent.get("keywords_raw") or ""),
            keywords_en=str(previous_intent.get("keywords_en") or ""),
        )

    if intent_override:
        # Khi nguoi dung sua/bo tag truc tiep tren giao diện
        base = parse_user_query(message, db_path=db_path, previous_intent=prev_obj, use_llm=use_llm) if message.strip() else (prev_obj or ChatIntent())
        if "wanted_genres" in intent_override:
            base.wanted_genres = [g for g in intent_override["wanted_genres"] if g in space.genre_to_col]
        if "avoid_genres" in intent_override:
            base.avoid_genres = [g for g in intent_override["avoid_genres"] if g in space.genre_to_col]
        if "similar_movie_ids" in intent_override:
            base.similar_movie_ids = [int(x) for x in intent_override["similar_movie_ids"]]
            base.similar_movie_titles = [
                space.movies[mid]["title"] for mid in base.similar_movie_ids if mid in space.movies
            ]
        if "matched_keywords" in intent_override:
            base.matched_keywords = list(intent_override["matched_keywords"] or [])
            base.matched_keyword_display = str(intent_override.get("matched_keyword_display") or "")
        if "year_from" in intent_override:
            base.year_from = intent_override["year_from"]
        if "year_to" in intent_override:
            base.year_to = intent_override["year_to"]
        if "max_runtime" in intent_override:
            base.max_runtime = intent_override["max_runtime"]
        intent = base
    else:
        intent = parse_user_query(message, db_path=db_path, previous_intent=prev_obj, use_llm=use_llm)

    if not intent_override and intent.is_empty():
        raise ValueError(
            "Hệ thống chưa hiểu yêu cầu tìm phim của bạn. "
            "Vui lòng mô tả tâm trạng, thể loại (hài, hành động...), "
            "thời kỳ hoặc tên phim cụ thể (VD: “giống Inception”)."
        )

    query_vec = build_query_vector(intent, space)
    query_scores = cosine_similarity_bulk(query_vec, space.matrix)

    # 4.2. HYBRID CONTENT SCORING: Ket hop Cosine 324 chieu voi Rich Content TF-IDF (12.000 features Anh + Viet)
    # Giai quyet triet de van de nen SVD 50 chieu lam mat tu khoa khi nguoi dung nhap mo ta cot truyen phim
    content_q_en = intent.content_query_en
    content_q_vi = intent.content_query_vi
    if (content_q_en or content_q_vi) and hasattr(space, "compute_content_similarity"):
        lex_scores = space.compute_content_similarity(content_q_en, content_q_vi)
        max_lex = float(np.max(lex_scores)) if len(lex_scores) else 0.0
        if max_lex > 0:
            # Chuan hoa tuong doi va cong huong manh vao query_scores cho cac phim khop sat noi dung
            norm_lex = lex_scores / max(max_lex, 0.22)
            query_scores = query_scores + 0.65 * norm_lex

    # 4.3. Tang diem vuot troi cho cac phim chua tu khoa TMDB duoc tim kiem
    kw_movie_ids: set[int] = set()
    if intent.matched_keywords and hasattr(space, "keyword_to_mids"):
        for kw in intent.matched_keywords:
            kw_movie_ids.update(space.keyword_to_mids.get(kw.lower(), set()))
    if kw_movie_ids:
        for idx, mid_np in enumerate(space.movie_ids):
            if int(mid_np) in kw_movie_ids:
                query_scores[idx] += 0.55

    # 4.35. Tang diem vuot troi cho cac bo phim do AI (LLM) suy luan truc tiep tu cot truyen
    if intent.ai_candidate_ids:
        ai_id_set = set(intent.ai_candidate_ids)
        for idx, mid_np in enumerate(space.movie_ids):
            if int(mid_np) in ai_id_set:
                query_scores[idx] += 0.85

    # 4.4. Tang diem truc tiep cho phim cua Dao dien / Dien vien (ke ca ngoai top 50/200 trong vector 324 chieu)
    if intent.director:
        for idx, mid_np in enumerate(space.movie_ids):
            meta = space.movies.get(int(mid_np))
            if meta and meta.get("director") == intent.director:
                query_scores[idx] += 0.65
    if intent.actor:
        for idx, mid_np in enumerate(space.movie_ids):
            meta = space.movies.get(int(mid_np))
            if meta and intent.actor in (meta.get("cast") or []):
                query_scores[idx] += 0.60

    # Kiem tra User Profile hien co cua nguoi dung
    prof = _rec._registry.get(user_id)
    history = get_user_interactions(user_id, db_path=db_path)
    interacted_ids = {int(h["movie_id"]) for h in history}
    liked_ids = [int(h["movie_id"]) for h in history if h["action"] == "like"]

    liked_genres: set[str] = set()
    for mid in liked_ids:
        if mid in space.movies:
            liked_genres.update(space.movies[mid]["genres"])

    has_profile = prof is not None and prof.is_initialized() and (len(liked_ids) > 0 or getattr(prof, "is_onboarded", False))
    if has_profile and prof.vector is not None:
        profile_scores = cosine_similarity_bulk(prof.vector, space.matrix)
        # Tron Cosine cua Query Vector (0.75) voi Cosine cua User Profile (0.25)
        w_q = float(np.clip(query_weight, 0.0, 1.0))
        blended_cosine = w_q * query_scores + (1.0 - w_q) * profile_scores
    else:
        profile_scores = None
        blended_cosine = query_scores

    # Tap phim can loai tru
    skip_ids = set(exclude_ids or set()) | interacted_ids | set(intent.similar_movie_ids)
    wanted_set = set(intent.wanted_genres)
    avoid_set = set(intent.avoid_genres)

    def _filter_pass(strict_genre: bool = True, strict_quality: bool = True) -> list[int]:
        passed: list[int] = []
        for idx, mid_np in enumerate(space.movie_ids):
            mid = int(mid_np)
            if mid in skip_ids:
                continue
            meta = space.movies.get(mid)
            if meta is None:
                continue
            m_genres = set(meta["genres"])
            # Luon loc cung the loai bi tranh (Avoid genres)
            if avoid_set and (m_genres & avoid_set):
                continue
            # Loc the loai muon (neu co)
            if strict_genre and wanted_set and not (m_genres & wanted_set):
                continue
            # Loc nam phat hanh
            year = meta.get("release_year")
            if intent.year_from and (year is None or year < intent.year_from):
                continue
            if intent.year_to and (year is None or year > intent.year_to):
                continue
            # Loc thoi luong (uu tien runtimes truyen vao, fallback sang space.mid_to_runtime tu DB/CSV)
            if intent.max_runtime:
                rt = (runtimes or {}).get(mid) or getattr(space, "mid_to_runtime", {}).get(mid)
                if rt and rt > intent.max_runtime:
                    continue
            # Loc nguong chat luong co ban de tranh phim rac it luot vote
            if strict_quality:
                if meta["vote_count"] < 50 or meta["vote_average"] < 5.5:
                    continue
            passed.append(idx)
        return passed

    valid_indices = _filter_pass(strict_genre=True, strict_quality=True)
    if len(valid_indices) < top_n:
        # Noi long nguong vote_count neu dieu kien nam/thoi luong qua hep
        valid_indices = _filter_pass(strict_genre=True, strict_quality=False)
    if len(valid_indices) < max(3, top_n // 2) and wanted_set:
        # Noi long strict_genre (de Query Cosine tu sap xep the loai gan nhat) nhung VAN GIU avoid_set
        valid_indices = _filter_pass(strict_genre=False, strict_quality=True)

    # Sap xep ung vien theo blended_cosine giam dan, lay candidate_k dua vao Multi-Objective Ranking
    valid_indices.sort(key=lambda idx: float(blended_cosine[idx]), reverse=True)
    top_indices = valid_indices[: max(candidate_k, top_n * 3)]

    candidates: list[dict[str, Any]] = []
    for idx in top_indices:
        mid = int(space.movie_ids[idx])
        meta = space.movies[mid]
        q_cos = float(query_scores[idx])
        p_cos = float(profile_scores[idx]) if profile_scores is not None else None
        b_cos = float(blended_cosine[idx])
        candidates.append({
            "movie_id": mid,
            "cosine": b_cos,
            "query_cosine": q_cos,
            "profile_cosine": p_cos,
            "title": meta["title"],
            "genres": meta["genres"],
            "director": meta["director"],
            "vote_average": meta["vote_average"],
            "popularity": meta["popularity"],
            "release_date": meta["release_date"],
        })

    # Dua qua Tang 1: Multi-Objective Ranking (Cosine 0.6 + Rating 0.2 + Popularity 0.1 + Newness 0.1)
    ranked = rank_candidates(candidates)
    # Dua qua Tang 2: Online SGD Reranker (neu user da co >=1 Like va >=1 Dislike)
    reranked = _apply_neural_reranking(
        user_id,
        ranked,
        db_path=db_path,
        neural_weight=0.15,
    )[:top_n]

    items: list[dict[str, Any]] = []
    for r in reranked:
        mid = int(r["movie_id"])
        meta = space.movies[mid]
        rt = (runtimes or {}).get(mid) or getattr(space, "mid_to_runtime", {}).get(mid)
        matched_kw_label = None
        if intent.matched_keywords and hasattr(space, "mid_to_keywords"):
            m_kws = {k.lower() for k in space.mid_to_keywords.get(mid, [])}
            for kw in intent.matched_keywords:
                if kw.lower() in m_kws:
                    matched_kw_label = kw
                    break
        why = _build_reason(
            meta=meta,
            intent=intent,
            query_cos=r["query_cosine"],
            profile_cos=r["profile_cosine"],
            runtime=rt,
            liked_genres=liked_genres,
            matched_kw_label=matched_kw_label,
        )
        items.append({
            "movie_id": mid,
            "title": meta["title"],
            "overview": meta["overview"],
            "genres": meta["genres"],
            "director": meta["director"],
            "cast": meta["cast"],
            "vote_average": meta["vote_average"],
            "popularity": meta["popularity"],
            "release_year": meta["release_year"],
            "runtime": rt,
            "why": why,
            "score": round(float(r.get("final_score", r.get("ranking_score", 0.0))), 4),
            "cosine": round(float(r["cosine"]), 4),
            "query_cosine": round(float(r["query_cosine"]), 4),
            "profile_cosine": round(float(r["profile_cosine"]), 4) if r["profile_cosine"] is not None else None,
            "neural_used": bool(r.get("neural_used")),
            "match_percent": round(max(0.0, min(1.0, float(r.get("final_score", 0.0)))) * 100),
            "breakdown": {
                "cosine": round(float(r.get("cosine_score", 0.0)), 3),
                "rating": round(float(r.get("rating_score", 0.0)), 3),
                "popularity": round(float(r.get("popularity_score", 0.0)), 3),
                "newness": round(float(r.get("newness_score", 0.0)), 3),
                "neural": round(float(r["nn_like_probability"]), 3) if r.get("neural_used") else None,
            },
        })

    return {
        "intent": intent.to_dict(),
        "personalized": has_profile,
        "items": items,
    }
