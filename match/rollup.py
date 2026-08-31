# reconcile/rollup.py
from __future__ import annotations
import json
from pathlib import Path


def row_judgment_summary(jsonl_path: Path) -> dict[str, dict]:
    """row_id -> {'verdicts': [...], 'accepted_ppns': [...]}"""
    summary: dict[str, dict] = {}
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("step") != "judgment":
                continue
            s = summary.setdefault(e["row_id"], {"verdicts": [], "accepted_ppns": []})
            s["verdicts"].append(e["verdict"])
            if e["verdict"] == "accept":
                s["accepted_ppns"].append(e["ppn"])
    return summary


def needs_retry(row_id: str, ranking: dict | None, judgments: dict) -> bool:
    if ranking is None or ranking.get("status") != "ok":
        return True  # no_candidates
    j = judgments.get(row_id)
    if j is None:
        return False  # not judged yet — not a retry case, just not processed
    return len(j["accepted_ppns"]) == 0  # nothing accepted -> retry