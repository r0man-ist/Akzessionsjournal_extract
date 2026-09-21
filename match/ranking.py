# match/ranking.py
from __future__ import annotations
import re
from dataclasses import dataclass
from collections import Counter

_PLACEHOLDER_RE = re.compile(r"\{!?[^{}!][^{}]*\}")

DEFAULT_TOLERANCE = 9


def specificity(template: str) -> int:
    """Number of distinct fields referenced in a CQL template — used as a proxy
    for how constrained/trustworthy a query is."""
    return len(_PLACEHOLDER_RE.findall(template))


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
    """
    Check that more specific queries never return MORE hits than less specific
    ones (each added field is an AND-constraint, so results should only shrink
    or stay flat). Returns human-readable messages for any violations found;
    empty list if everything behaves as expected.
    """
    entries = [
        (name, specificity(info["template"]), info["n_results"])
        for name, info in candidates.items()
    ]
    entries.sort(key=lambda e: e[1])  # sort by specificity, ascending

    violations = []
    for i, (lo_name, lo_spec, lo_n) in enumerate(entries):
        for hi_name, hi_spec, hi_n in entries[i + 1:]:
            if hi_spec > lo_spec and hi_n > lo_n:
                violations.append(
                    f"{hi_name} (specificity {hi_spec}, n={hi_n}) > "
                    f"{lo_name} (specificity {lo_spec}, n={lo_n})"
                )
    return violations