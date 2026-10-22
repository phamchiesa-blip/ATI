"""Small ranking metrics and comparison helpers; no project data dependency."""

from __future__ import annotations

from typing import Callable, Iterable


def precision_recall_f1_at_k(ranked_ids: Iterable, relevant_ids: Iterable, k: int) -> dict[str, float]:
    if k <= 0:
        raise ValueError("k must be greater than zero")
    ranked = list(ranked_ids)[:k]
    relevant = set(relevant_ids)
    hits = sum(1 for movie_id in ranked if movie_id in relevant)
    precision = hits / k
    recall = hits / len(relevant) if relevant else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def compare_rankers(
    cases: Iterable[dict],
    baseline: Callable[[list[dict]], list[dict]],
    proposed: Callable[[list[dict]], list[dict]],
    *,
    k: int = 10,
) -> dict[str, dict[str, float]]:
    """Average Precision/Recall/F1 over cases.

    Each case has ``candidates`` (dicts with movie_id), ``relevant_ids``, and
    optionally ``is_new_user``. Results contain overall and new-user metrics.
    """
    buckets = {"baseline": {"all": [] , "new_user": []}, "proposed": {"all": [], "new_user": []}}
    for case in cases:
        candidates = [dict(row) for row in case["candidates"]]
        relevant = case["relevant_ids"]
        for name, ranker in (("baseline", baseline), ("proposed", proposed)):
            ranked = ranker(candidates)
            metric = precision_recall_f1_at_k(
                [row["movie_id"] for row in ranked], relevant, k
            )
            buckets[name]["all"].append(metric)
            if case.get("is_new_user", False):
                buckets[name]["new_user"].append(metric)

    result = {}
    for name, groups in buckets.items():
        result[name] = {}
        for group, values in groups.items():
            for metric in ("precision", "recall", "f1"):
                result[name][f"{group}_{metric}@{k}"] = (
                    sum(item[metric] for item in values) / len(values) if values else 0.0
                )
    return result
