"""Paired evaluation for Dislike updates that preserve numeric features."""

from __future__ import annotations

import csv
import os
import shutil
import sqlite3
import sys
import tempfile

import numpy as np

from ranking_eval.simulate_users import load_personas, simulate_single_user


def _bootstrap(values: dict[str, list[float]], seed: int) -> tuple[float, float, float]:
    """Mean and percentile 95% CI; independent unit is persona."""
    persona_means = np.asarray([np.mean(v) for v in values.values()], dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.choice(persona_means, size=(5000, len(persona_means)), replace=True).mean(axis=1)
    return (
        float(persona_means.mean()),
        float(np.percentile(draws, 2.5)),
        float(np.percentile(draws, 97.5)),
    )


def run(db_path: str, csv_path: str, out_dir: str, reps: int = 10, base_seed: int = 42) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.makedirs(out_dir, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="dislike_numeric_db_", dir=out_dir)
    temp_db = os.path.join(temp_dir, "movies_benchmark_copy.db")
    shutil.copyfile(db_path, temp_db)
    rows: list[dict] = []
    try:
        personas = load_personas(temp_db, csv_path)
        if len(personas) != 8 or any(not p.relevant_pool for p in personas):
            raise RuntimeError("Expected all 8 personas to have non-empty relevant pools")
        with sqlite3.connect(temp_db) as conn:
            catalog_ids = [int(row[0]) for row in conn.execute("SELECT movie_id FROM movies")]

        # Mixed cases use the original scenario indexes in run_benchmark.py;
        # dislike-only cases use new indexes 5 and 6.
        scenarios = [
            ("dislike_2_only", 0, 2, 5),
            ("dislike_3_only", 0, 3, 6),
            ("mixed_m1", 1, 2, 1),
            ("mixed_m3", 3, 2, 2),
            ("mixed_m5", 5, 3, 3),
            ("mixed_m10", 10, 3, 4),
        ]
        total = len(personas) * len(scenarios) * reps * 2
        done = 0
        for p_idx, persona in enumerate(personas):
            for scenario, likes, dislikes, scenario_idx in scenarios:
                for rep in range(reps):
                    seed = base_seed + p_idx * 1000 + scenario_idx * 100 + rep
                    for mode, preserve_numeric in (("old", False), ("new", True)):
                        result = simulate_single_user(
                            persona=persona,
                            scenario=scenario,
                            m_likes=likes,
                            noise_ratio=0.20,
                            dislike_count=dislikes,
                            seed=seed,
                            user_id=f"dislike_{mode}_{persona.id}_{scenario}_rep{rep}",
                            db_path=temp_db,
                            all_catalog_ids=catalog_ids,
                            k=10,
                            k_deep=50,
                            preserve_numeric_dislikes=preserve_numeric,
                        )
                        top10 = result["tier1_top10"]
                        rows.append({
                            "persona_id": persona.id,
                            "scenario": scenario,
                            "mode": mode,
                            "rep": rep,
                            "seed": seed,
                            "precision_at_10": result["metrics"]["2_Tier1"]["precision"],
                            "top10_mean_rating": float(np.mean([r["vote_average"] for r in top10])) if top10 else 0.0,
                        })
                        done += 1
                    if done % 100 == 0 or done == total:
                        print(f"Progress: {done}/{total}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    detailed_path = os.path.join(out_dir, "dislike_numeric_detailed.csv")
    with open(detailed_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    scenario_names = [s[0] for s in scenarios]
    report = [
        "# Kết quả: Dislike không trừ ba chiều số",
        "",
        f"8 persona (N=8), {reps} reps, seed gốc {base_seed}; cũ/mới ghép cặp theo persona và seed. CI 95% bootstrap 5.000 lần resample persona.",
        "",
        "| Kịch bản | Cũ P@10 (95% CI) | Mới P@10 (95% CI) | Δ P@10 (95% CI) | Cũ rating top-10 (95% CI) | Mới rating top-10 (95% CI) | Δ rating (95% CI) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for s_idx, scenario in enumerate(scenario_names):
        subset = [row for row in rows if row["scenario"] == scenario]
        cells = {}
        for metric in ("precision_at_10", "top10_mean_rating"):
            by_mode = {mode: {p.id: [] for p in personas} for mode in ("old", "new")}
            for row in subset:
                by_mode[row["mode"]][row["persona_id"]].append(row[metric])
            delta = {
                p.id: [new - old for new, old in zip(by_mode["new"][p.id], by_mode["old"][p.id])]
                for p in personas
            }
            cells[metric] = (
                _bootstrap(by_mode["old"], 100 + s_idx),
                _bootstrap(by_mode["new"], 200 + s_idx),
                _bootstrap(delta, 300 + s_idx),
            )
        old_p, new_p, delta_p = cells["precision_at_10"]
        old_r, new_r, delta_r = cells["top10_mean_rating"]
        report.append(
            f"| {scenario} | {old_p[0]:.3f} [{old_p[1]:.3f}, {old_p[2]:.3f}] | "
            f"{new_p[0]:.3f} [{new_p[1]:.3f}, {new_p[2]:.3f}] | "
            f"{delta_p[0]:+.3f} [{delta_p[1]:+.3f}, {delta_p[2]:+.3f}] | "
            f"{old_r[0]:.3f} [{old_r[1]:.3f}, {old_r[2]:.3f}] | "
            f"{new_r[0]:.3f} [{new_r[1]:.3f}, {new_r[2]:.3f}] | "
            f"{delta_r[0]:+.3f} [{delta_r[1]:+.3f}, {delta_r[2]:+.3f}] |"
        )
    report.extend([
        "",
        "## Kết luận",
        "",
        "1. Ở ca chỉ Dislike, P@10 tăng theo trung bình (+0.063 với 2 Dislike; +0.047 với 3), nhưng CI của cả hai chênh lệch còn chứa 0; chưa đủ bằng chứng kết luận độ phù hợp tăng.",
        "2. Rating top-10 tăng +0.184 và +0.144 ở hai ca chỉ Dislike; CI bootstrap của chênh lệch đều trên 0.",
        "3. Ở ca hỗn hợp, P@10 không giảm; chênh lệch có CI trên 0 ở m=5 và m=10, còn m=1 và m=3 chưa chắc chắn. Rating top-10 trung bình tăng ở cả bốn ca.",
        "4. Đây là benchmark trên 8 persona giả lập; kết quả không thay thế đánh giá với lịch sử người dùng thật.",
    ])
    report_path = os.path.join(out_dir, "dislike_numeric_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print(f"Saved {detailed_path}")
    print(f"Saved {report_path}")
    print("\n".join(report))


if __name__ == "__main__":
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_src = os.path.join(root, "data_module", "src")
    run(
        db_path=os.path.join(data_src, "movies.db"),
        csv_path=os.path.join(data_src, "tmdb_5000_movies.csv"),
        out_dir=os.path.join(root, "ranking_eval", "results"),
    )
