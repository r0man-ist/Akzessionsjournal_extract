# match/ranking.py
from __future__ import annotations
import re
from dataclasses import dataclass
from collections import Counter


DEFAULT_TOLERANCE = 9


_PLACEHOLDER_NAME_RE = re.compile(r"\{!?([^{}]+)\}")

FIELD_WEIGHTS = {
    "title_search": 4.0,
    "author_last": 1.5,
    "Jahr_CQL": 1.0,
    "publication_place_normalized": 0.5,
}

DEFAULT_WEIGHT = 1.0


def template_fields(template: str) -> set[str]:
    return set(_PLACEHOLDER_NAME_RE.findall(template or ""))


def specificity(template: str) -> float:
    """Weighted specificity: title dominates, place counts least."""
    return sum(FIELD_WEIGHTS.get(f, DEFAULT_WEIGHT) for f in template_fields(template))


def is_plausible(n: int, expected: float | None, tolerance: int = DEFAULT_TOLERANCE) -> bool:
    """A tier is plausible if it returned hits and, when an expected count is
    known, no more than expected + tolerance of them."""
    if n <= 0:
        return False
    if expected and expected > 0:
        return n <= expected + tolerance
    return True


@dataclass
class RankedCandidate:
    query_name: str
    template: str
    n_results: int
    ppns: list[str]
    specificity: int
    overlap_score: int = 0


def rank_candidates(
    candidates: dict[str, dict],
    expected: float | None,
    tolerance: int = DEFAULT_TOLERANCE,
) -> list[RankedCandidate]:
    """
    candidates: query_name -> {"n_results": int, "ppns": [...], "template": str}
    (the shape of candidate_index[row_id] from rank.py / the notebook)

    Returns only plausible tiers (see is_plausible), ranked best-first by:
      1. specificity (more constrained query first)
      2. closeness of n_results to the expected count
      3. overlap with other plausible tiers

    Returns an empty list if no tier is plausible — callers must handle that.
    """
    entries = [
        RankedCandidate(
            query_name=name,
            template=info["template"],
            n_results=info["n_results"],
            ppns=info["ppns"],
            specificity=specificity(info["template"]),
        )
        for name, info in candidates.items()
        if is_plausible(info["n_results"], expected, tolerance)
    ]

    # overlap: how many other plausible tiers also surfaced each PPN
    ppn_counts = Counter()
    for e in entries:
        ppn_counts.update(set(e.ppns))
    for e in entries:
        e.overlap_score = sum(ppn_counts[p] - 1 for p in e.ppns)

    def sort_key(e: RankedCandidate):
        closeness = abs(e.n_results - expected) if expected else 0
        return (-e.specificity, closeness, -e.overlap_score)

    return sorted(entries, key=sort_key)

def find_monotonicity_violations(candidates: dict[str, dict]) -> list[str]:
    entries = [(name, template_fields(info["template"]), info["n_results"])
               for name, info in candidates.items()]
    violations = []
    for lo_name, lo_f, lo_n in entries:
        for hi_name, hi_f, hi_n in entries:
            if lo_f < hi_f and hi_n > lo_n:          # hi adds constraints but has more hits
                violations.append(f"{hi_name} (n={hi_n}) > {lo_name} (n={lo_n})")
    return violations