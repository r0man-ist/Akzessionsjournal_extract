from __future__ import annotations
import json
from turtle import done
import uuid
from datetime import datetime, timezone
from pathlib import Path


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EventLogger:
    """Append-only JSONL writer. One line per event, never rewritten or edited."""

    def __init__(self, path: Path, run_id: str | None = None):
        self.path = Path(path)
        self.run_id = run_id or new_run_id()
        self._fh = open(self.path, "a", encoding="utf-8")

    def log(self, row_id: str, step: str, **fields) -> None:
        event = {"row_id": row_id, "run_id": self.run_id, "ts": now_iso(), "step": step, **fields}
        self._fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._fh.flush()  # crash mid-batch shouldn't lose already-logged rows

    def already_done(self) -> set[tuple[str, str, str | None]]:
        """Scan the log for (row_id, step, query_name) triples representing work
        that doesn't need to be redone. query_name is None for row-level steps
        like year_normalize that aren't per-template.
        """
        done = set()
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    e = json.loads(line)
                    step = e.get("step")

                    if step == "sru_search" and e.get("status") != "skipped_empty":
                        done.add((e["row_id"], "sru_search", e.get("query_name")))

                    elif step == "year_normalize":
                        done.add((e["row_id"], "year_normalize", None))
        return done

    def close(self):
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()