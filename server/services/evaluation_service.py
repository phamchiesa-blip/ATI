import csv
import os
import re
from typing import Optional

from server.config import EVAL_DIR

RANKER_LABELS = {
    "0a_Random": ("Ngẫu nhiên", "reference"),
    "0b_Popular": ("Phổ biến nhất", "reference"),
    "1_Baseline": ("Baseline (chỉ cosine)", "baseline"),
    "2_Tier1": ("Tầng 1 (Ranking)", "tier1"),
    "3_Tier2_Old": ("Tầng 2 cũ (xác suất)", "tier2old"),
    "3_Tier2_New": ("Tầng 2 mới (logit chuẩn hóa)", "tier2new"),
}
SCENARIO_LABELS = {
    "ALL": "Tổng thể",
    "onboarding_only": "Chỉ chọn thể loại",
    "interactions_m1": "Thích 1 phim",
    "interactions_m3": "Thích 3 phim",
    "interactions_m5": "Thích 5 phim",
    "interactions_m10": "Thích 10 phim",
}
EVAL_METRICS = [
    ("precision_at_10", "Precision@10", "Trong 10 phim đầu được gợi ý, tỷ lệ phim thật sự hợp gu người dùng giả lập."),
    ("hit_rate_at_10", "Hit rate@10", "Tỷ lệ người dùng giả lập có ít nhất 1 phim hợp gu trong 10 phim đầu."),
    ("recall_at_10", "Recall@10", "Trong toàn bộ phim hợp gu, tỷ lệ tìm thấy trong 10 phim đầu (thấp là bình thường vì có hàng trăm phim hợp gu)."),
    ("recall_at_50", "Recall@50", "Như Recall@10 nhưng tính trong 50 phim đầu."),
    ("f1_at_10", "F1@10", "Điểm cân bằng giữa Precision@10 và Recall@10."),
]
_LATEX = {r"\Delta": "Δ", r"\approx": "≈", r"\lambda": "λ", r"\in": "∈", r"\{": "{", r"\}": "}", r"\pm": "±"}


def clean_md(text: str) -> str:
    for k, v in _LATEX.items():
        text = text.replace(k, v)
    return re.sub(r"[*`$]", "", text).replace("\\", "").strip()


def md_tables(text: str) -> list:
    """Lay moi bang markdown cung tieu de gan nhat phia tren."""
    out, heading, block = [], "", []

    def flush():
        if len(block) >= 3:
            cells = lambda ln: [clean_md(c) for c in ln.strip().strip("|").split("|")]
            out.append({"heading": clean_md(heading.lstrip("# ")), "header": cells(block[0]),
                        "rows": [cells(ln) for ln in block[2:]]})
        block.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            block.append(line.strip())
            continue
        flush()
        if line.startswith("#"):
            heading = line
    flush()
    return out


def numbered(text: str) -> list:
    """'1. **Tieu de**: noi dung' va cac dong '- y nho' ben duoi -> [{title, text, points}]"""
    blocks = []
    for line in text.splitlines():
        m = re.match(r"^\d+\.\s+\*\*(.+?)\*\*\s*:?\s*(.*)$", line)
        if m:
            blocks.append({"title": clean_md(m.group(1)).rstrip(":"), "text": clean_md(m.group(2)), "points": []})
        elif blocks and re.match(r"^\s+[-*]\s+", line):
            blocks[-1]["points"].append(clean_md(re.sub(r"^\s+[-*]\s+", "", line)))
    return blocks


def read_file(name: str) -> Optional[str]:
    path = os.path.join(EVAL_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig") as f:
        return f.read().replace("\r\n", "\n")


def get_evaluation_data() -> dict:
    summary_text = read_file("benchmark_summary.csv")
    report = read_file("benchmark_report.md")
    if summary_text is None:
        return {"available": False}
    rows = list(csv.DictReader(summary_text.splitlines()))
    num = lambda v: float(v) if v not in (None, "") else None

    summary, personas = {}, {}
    for r in rows:
        if r["group_type"] in ("overall", "scenario"):
            sid = "ALL" if r["group_type"] == "overall" else r["scenario"]
            cell = summary.setdefault(sid, {}).setdefault(r["ranker"], {})
            for key, _, _ in EVAL_METRICS:
                cell[key] = {"mean": num(r[f"{key}_mean"]), "std": num(r[f"{key}_std"])}
        elif r["group_type"] == "persona":
            m = re.match(r"^(\w+)\s*\((.*)\)$", r["persona_id"])
            pid, pname = (m.group(1), m.group(2)) if m else (r["persona_id"], "")
            p = personas.setdefault(pid, {"id": pid, "name": pname, "precision": {}})
            p["precision"][r["ranker"]] = num(r["precision_at_10_mean"])
    detailed = read_file("benchmark_detailed.csv")
    if detailed:
        for r in csv.DictReader(detailed.splitlines()):
            p = personas.get(r["persona_id"])
            if p is not None and "external" not in p:
                p["external"] = r["is_external"] == "True"
                p["pool_size"] = int(float(r["pool_size"]))

    order = ["ALL", "onboarding_only", "interactions_m1", "interactions_m3", "interactions_m5", "interactions_m10"]
    scenario_ids = [x for x in order if x in summary] + [x for x in summary if x not in order]
    ranker_ids = sorted({k for sc in summary.values() for k in sc})

    out = {
        "available": True,
        "rankers": [
            {"id": r, "label": RANKER_LABELS.get(r, (r, "other"))[0], "kind": RANKER_LABELS.get(r, (r, "other"))[1]}
            for r in ranker_ids
        ],
        "scenarios": [{"id": x, "label": SCENARIO_LABELS.get(x, x)} for x in scenario_ids],
        "metrics": [{"id": k, "label": lab, "hint": hint} for k, lab, hint in EVAL_METRICS],
        "summary": summary,
        "personas": sorted(personas.values(), key=lambda p: p["id"]),
        "run_info": [],
        "paired": None,
        "conclusions": [],
        "limitations": [],
        "dislike": None,
    }
    if report:
        out["run_info"] = [clean_md(ln.lstrip("> ")) for ln in report.splitlines()[:6] if ln.startswith(">")]
        out["paired"] = next((t for t in md_tables(report) if "Bảng 2" in t["heading"]), None)
        a = report.find("### Nhận định")
        b = report.find("\n## ", a + 5) if a >= 0 else -1
        if a >= 0:
            out["conclusions"] = numbered(report[a : b if b > 0 else None])
        c = report.find("## 6.")
        if c >= 0:
            out["limitations"] = numbered(report[c:])
    dislike = read_file("dislike_numeric_report.md")
    if dislike:
        tables = md_tables(dislike)
        k = dislike.find("## Kết luận")
        out["dislike"] = {
            "title": clean_md(dislike.splitlines()[0].lstrip("# ")),
            "table": tables[0] if tables else None,
            "notes": [
                clean_md(re.sub(r"^\d+\.\s+", "", ln))
                for ln in dislike[k:].splitlines()
                if re.match(r"^\d+\.\s+", ln)
            ]
            if k >= 0
            else [],
        }
    return out

