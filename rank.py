# rank_batch.py
from __future__ import annotations
import argparse
import json
from pathlib import Path

import pandas as pd

from match.ranking import rank_candidates, find_monotonicity_violations
from utils.jsonl_log import EventLogger


def build_candidate_index(jsonl_path: Path) -> dict[str, dict[str, dict]]:
    """row_id -> {query_name: {n_results, ppns, template}}, from sru_search events."""
    index: dict[str, dict[str, dict]] = {}
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("step") != "sru_search" or e.get("status") == "skipped_empty":
                continue
            index.setdefault(e["row_id"], {})[e["query_name"]] = {
                "n_results": e.get("n_results", 0),
                "ppns": e.get("ppns", []),
                "template": e.get("template"),
            }
    return index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("--uid-col", default="Lfd. Nr.")
    parser.add_argument("--expected-col", default="Zahl")
    parser.add_argument("--sep", default=";")
    parser.add_argument("--tolerance", type=float, default=3.0)
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv, sep=args.sep, dtype=str)
    candidate_index = build_candidate_index(args.input_jsonl)

    with EventLogger(args.input_jsonl) as logger:  # same file, appends new events
        for _, row in df.iterrows():
            row_id = str(row[args.uid_col])
            candidates = candidate_index.get(row_id)
            if not candidates:
                continue

            expected = pd.to_numeric(row[args.expected_col], errors="coerce")
            expected = None if pd.isna(expected) else float(expected)

            for msg in find_monotonicity_violations(candidates):
                logger.log(row_id, "monotonicity_violation", detail=msg, expected=expected)

            if all(info["n_results"] == 0 for info in candidates.values()):
                logger.log(row_id, "ranking", status="no_candidates", expected=expected)
                continue

            ranked = rank_candidates(candidates, expected=expected, tolerance=args.tolerance)
            best = ranked[0]

            logger.log(row_id, "ranking", status="ok",
                    chosen_query_name=best.query_name,
                    specificity=best.specificity,
                    n_results=best.n_results,
                    overlap_score=best.overlap_score,
                    plausible=best.plausible,
                    ppns=best.ppns,
                    expected=expected)

    print(f"Logged ranking events for {len(candidate_index)} rows to {args.input_jsonl}")


if __name__ == "__main__":
    main()