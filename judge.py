from __future__ import annotations
import argparse
import json
import logging
import time
from pathlib import Path

import pandas as pd
from openai import OpenAI

from match.config import (
    BASE_URL,
    MAX_RETRIES,
    MAX_TOKENS,
    MODEL,
    RETRY_BACKOFF_BASE,
    TEMPERATURE,
    TIMEOUT,
    REASONING
)
from match.models import JudgmentResult
from match.prompts import SYSTEM_PROMPT, USER_PROMPT
from utils.jsonl_log import EventLogger
from utils.llm import build_client, response_format
from utils.sru import get_record

logger = logging.getLogger(__name__)


def judge_candidate(client: OpenAI, row: dict, record_xml: str, ppn: str) -> JudgmentResult:
    prompt = USER_PROMPT.format(Titel=row.get("Titel"), record_xml=record_xml)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                response_format=response_format(JudgmentResult, "JudgmentResult"),
                extra_body={"reasoning": REASONING},
                messages=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": SYSTEM_PROMPT,
                                "cache_control": {"type": "ephemeral"},
                            }
                        ],
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            error = getattr(response, "error", None)
            if error:
                raise RuntimeError(f"OpenRouter returned an error: {error}")
            if not response.choices:
                raise RuntimeError(f"No choices in response: {response.model_dump()}")

            content = response.choices[0].message.content
            if not content:
                raise RuntimeError(f"Empty content in response: {response.model_dump()}")

            return JudgmentResult.model_validate_json(content)

        except Exception as e:
            logger.warning(
                "Judgment attempt %d/%d failed for PPN %s: %s",
                attempt, MAX_RETRIES, ppn, e,
            )
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE ** attempt)

    return JudgmentResult(
        verdict="uncertain",
        confidence="low",
        reasoning=f"LLM call failed after {MAX_RETRIES} attempts: {last_error}"[:150],
)


def latest_ranking_events(jsonl_path: Path) -> dict[str, dict]:
    """row_id -> most recent 'ranking' event (by file order, last one wins)."""
    latest: dict[str, dict] = {}
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("step") == "ranking":
                latest[e["row_id"]] = e
    return latest


def already_judged(jsonl_path: Path) -> set[tuple[str, str]]:
    """(row_id, ppn) pairs that already have a judgment logged."""
    done = set()
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("step") == "judgment":
                done.add((e["row_id"], e["ppn"]))
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("--uid-col", default="Lfd. Nr.")
    parser.add_argument("--catalogue", choices=["k10plus", "stabikat", "VD17"], default="stabikat")
    parser.add_argument("--sep", default=";")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    client = build_client(BASE_URL, TIMEOUT)
    df = pd.read_csv(args.input_csv, sep=args.sep, dtype=str)

    rankings = latest_ranking_events(args.input_jsonl)
    skip = already_judged(args.input_jsonl)

    with EventLogger(args.input_jsonl) as event_logger:
        for _, row in df.iterrows():
            row_id = str(row[args.uid_col])
            ranking = rankings.get(row_id)

            if ranking is None or ranking.get("status") != "ok":
                continue  # no candidates, or needs the retry step first

            for ppn in ranking["ppns"]:
                if (row_id, ppn) in skip:
                    continue

                try:
                    record_xml = get_record(ppn, catalogue=args.catalogue)
                except Exception as e:
                    logger.warning("Failed to fetch record %s for row %s: %s", ppn, row_id, e)
                    event_logger.log(row_id, "judgment", ppn=ppn, judged_by="llm",
                                      verdict="uncertain", confidence="low",
                                      reasoning=f"record fetch failed: {e}"[:150])
                    continue

                result = judge_candidate(client, row.to_dict(), record_xml, ppn)
                event_logger.log(row_id, "judgment", ppn=ppn, judged_by="llm",
                                  verdict=result.verdict, confidence=result.confidence,
                                  reasoning=result.reasoning)
                logger.info("Judged row %s / PPN %s -> %s", row_id, ppn, result.verdict)

    print(f"Judged candidates for {len(rankings)} ranked rows, logged to {args.input_jsonl}")


if __name__ == "__main__":
    main()