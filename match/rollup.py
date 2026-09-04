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
    if ranking is None:
        return False  # not yet ranked — not a retry case
    if ranking.get("status") != "ok":
        return True   # ranked but no candidates found
    j = judgments.get(row_id)
    if j is None:
        return False  # ranked and has candidates, but not yet judged
    return len(j["accepted_ppns"]) == 0  # judged but nothing accepted