"""Standalone ranking, baseline, optional online model, and evaluation helpers.

This package deliberately has no imports from ``data_module`` or
``recommendation``. Callers pass candidate scores and movie metadata in.
"""

from .ranking import RankingWeights, rank_candidates, baseline_rank
from .evaluation import precision_recall_f1_at_k, compare_rankers

__all__ = [
    "RankingWeights",
    "rank_candidates",
    "baseline_rank",
    "precision_recall_f1_at_k",
    "compare_rankers",
]
