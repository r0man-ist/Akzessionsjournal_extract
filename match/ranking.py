# utils/ranking.py
from __future__ import annotations
import re
from dataclasses import dataclass
from collections import Counter

_PLACEHOLDER_RE = re.compile(r"\{!?[^{}!][^{}]*\}")


def specificity(template: str) -> int:
    """Number of distinct fields referenced in a CQL template — used as a proxy
    for how constrained/trustworthy a query is."""
    return len(_PLACEHOLDER_RE.findall(template))


@dataclass
class RankedCandidate:
    query_name: str
    template: str
    n_results: int
    ppns: list[str]
    specificity: int
    plausible: bool
    overlap_score: int = 0


def rank_candidates(
    candidates: dict[str, dict],
    expected: float | None,
    tolerance: float = 3.0,
) -> list[RankedCandidate]:
    """
    candidates: query_name -> {"n_results": int, "ppns": [...], "template": str}
    (this is exactly the shape of candidate_index[row_id] from the notebook)

    Returns candidates ranked best-first. Callers should only trust ranked[0]
    if ranked[0].plausible is True.
    """
    entries = []
    for name, info in candidates.items():
        n = info["n_results"]
        plausible = n > 0
        if plausible and expected and expected > 0:
            plausible = n <= expected * tolerance
        entries.append(RankedCandidate(
            query_name=name, template=info["template"], n_results=n,
            ppns=info["ppns"], specificity=specificity(info["template"]),
            plausible=plausible,
        ))

    # overlap: how many other tiers also surfaced each PPN
    ppn_counts = Counter()
    for e in entries:
        ppn_counts.update(set(e.ppns))
    for e in entries:
        e.overlap_score = sum(ppn_counts[p] - 1 for p in e.ppns)

    def sort_key(e: RankedCandidate):
        closeness = abs(e.n_results - expected) if expected else 0
        return (not e.plausible, -e.specificity, closeness, -e.overlap_score)

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