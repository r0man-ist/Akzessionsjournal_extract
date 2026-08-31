# match/retry_batch.py
from __future__ import annotations
import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from match.config import BASE_URL, MAX_TOKENS, MODEL, TEMPERATURE, TIMEOUT, REASONING
from judge import judge_candidate
from match.models import DiagnosisResult
from match.prompts import RETRY_SYSTEM_PROMPT, RETRY_USER_PROMPT
from match.ranking import specificity
from match.rollup import needs_retry, row_judgment_summary
from utils.jsonl_log import EventLogger
from utils.llm import build_client, response_format
from utils.sru import get_record, run_query

logger = logging.getLogger(__name__)

MAX_LLM_RETRIES_PER_ROW = 2


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


def retry_count(jsonl_path: Path, row_id: str) -> int:
    """How many LLM-triggered retry searches have already run for this row."""
    count = 0
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if (e.get("row_id") == row_id and e.get("step") == "sru_search"
                    and e.get("triggered_by") == "llm_retry"):
                count += 1
    return count


def format_attempts(jsonl_path: Path, row_id: str) -> str:
    lines = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            if e.get("row_id") == row_id and e.get("step") == "sru_search":
                if e.get("status") == "skipped_empty":
                    lines.append(f"- (skipped, missing data) -> 0 results")
                else:
                    q = e.get("query", e.get("template"))
                    lines.append(f"- {q} -> {e.get('n_results', '?')} results")
    return "\n".join(lines) or "(no prior attempts)"


def diagnose_failure(client, row: dict, attempts_text: str) -> DiagnosisResult | None:
    prompt = RETRY_USER_PROMPT.format(Titel=row.get("Titel"), attempts=attempts_text)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            response_format=response_format(DiagnosisResult, "DiagnosisResult"),
            extra_body={"reasoning": REASONING},
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": RETRY_SYSTEM_PROMPT,
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

        return DiagnosisResult.model_validate_json(content)

    except Exception as e:
        logger.warning("Diagnosis failed for row: %s", e)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("--uid-col", default="Lfd. Nr.")
    parser.add_argument("--expected-col", default="Zahl")
    parser.add_argument("--catalogue", choices=["k10plus", "stabikat", "VD17"], default="stabikat")
    parser.add_argument("--sep", default=";")
    parser.add_argument("--tolerance", type=float, default=3.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    client = build_client(BASE_URL, TIMEOUT)
    df = pd.read_csv(args.input_csv, sep=args.sep, dtype=str)

    rankings = latest_ranking_events(args.input_jsonl)
    judgments = row_judgment_summary(args.input_jsonl)

    with EventLogger(args.input_jsonl) as event_logger:
        for _, row in df.iterrows():
            row_id = str(row[args.uid_col])
            ranking = rankings.get(row_id)

            if not needs_retry(row_id, ranking, judgments):
                continue

            if retry_count(args.input_jsonl, row_id) >= MAX_LLM_RETRIES_PER_ROW:
                event_logger.log(row_id, "retry_exhausted", note="max LLM retries reached")
                continue

            attempts_text = format_attempts(args.input_jsonl, row_id)
            diagnosis = diagnose_failure(client, row.to_dict(), attempts_text)

            if diagnosis is None:
                event_logger.log(row_id, "retry_diagnosis_failed")
                continue

            event_logger.log(row_id, "retry_diagnosis",
                              proposed_query=diagnosis.proposed_query,
                              failure_reason=diagnosis.failure_reason,
                              reasoning=diagnosis.reasoning)

            try:
                n_results, ppns = run_query(diagnosis.proposed_query, catalogue=args.catalogue)
            except Exception as e:
                logger.warning("Retry query failed for row %s: %s", row_id, e)
                event_logger.log(row_id, "sru_search", query_name="llm_retry",
                                  template="llm_retry_freetext", query=diagnosis.proposed_query,
                                  catalogue=args.catalogue, status="query_error", error=str(e),
                                  triggered_by="llm_retry")
                continue

            event_logger.log(row_id, "sru_search", query_name="llm_retry",
                              template="llm_retry_freetext", query=diagnosis.proposed_query,
                              catalogue=args.catalogue, n_results=n_results, ppns=ppns,
                              triggered_by="llm_retry")

            expected = pd.to_numeric(row[args.expected_col], errors="coerce")
            expected = None if pd.isna(expected) else float(expected)
            plausible = n_results > 0 and (not expected or n_results <= expected * args.tolerance)

            if plausible:
                event_logger.log(row_id, "ranking", status="ok", chosen_query_name="llm_retry",
                                  specificity=specificity("llm_retry_freetext"),
                                  n_results=n_results, overlap_score=0, plausible=True,
                                  ppns=ppns, expected=expected)

                for ppn in ppns:
                    try:
                        record_xml = get_record(ppn, catalogue=args.catalogue)
                    except Exception as e:
                        logger.warning("Failed to fetch record %s for row %s: %s", ppn, row_id, e)
                        event_logger.log(row_id, "judgment", ppn=ppn, judged_by="llm",
                                          verdict="uncertain", confidence="low",
                                          reasoning=f"record fetch failed: {e}")
                        continue

                    result = judge_candidate(client, row.to_dict(), record_xml, ppn)
                    event_logger.log(row_id, "judgment", ppn=ppn, judged_by="llm",
                                      verdict=result.verdict, confidence=result.confidence,
                                      reasoning=result.reasoning)
                    logger.info("Retried judgment row %s / PPN %s -> %s", row_id, ppn, result.verdict)
            else:
                event_logger.log(row_id, "ranking", status="no_candidates", expected=expected)

    print(f"Retry pass complete, logged to {args.input_jsonl}")


if __name__ == "__main__":
    main()