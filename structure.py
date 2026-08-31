from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from structure.config import (
    BASE_URL,
    INPUT_COLUMN,
    INPUT_CSV,
    MAX_RETRIES,
    MAX_TOKENS,
    MODEL,
    OUTPUT_CSV,
    REASONING,
    RETRY_BACKOFF_BASE,
    TEMPERATURE,
    TIMEOUT,
)
from structure.models import BibliographicRecord
from structure.prompts import SYSTEM_PROMPT, USER_PROMPT
from utils.llm import response_format, build_client

logger = logging.getLogger(__name__)


def parse_reference(client: OpenAI, reference: str) -> BibliographicRecord:
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                response_format=response_format(BibliographicRecord, "BibliographicRecord"),
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
                    {
                        "role": "user",
                        "content": USER_PROMPT.format(reference=reference),
                    },
                ],
            )

            # OpenRouter sometimes returns HTTP 200 with choices=None and the
            # real problem tucked into an `error` field instead of raising.
            error = getattr(response, "error", None)
            if error:
                raise RuntimeError(f"OpenRouter returned an error: {error}")

            if not response.choices:
                raise RuntimeError(
                    f"No choices in response: {response.model_dump()}"
                )

            content = response.choices[0].message.content

            if not content:
                raise RuntimeError(
                    f"Empty content in response: {response.model_dump()}"
                )

            return BibliographicRecord.model_validate_json(content)

        except Exception as e:
            logger.warning(
                "Attempt %d/%d failed for reference %r: %s",
                attempt,
                MAX_RETRIES,
                reference,
                e,
            )
            last_error = e
            if attempt < MAX_RETRIES:
                sleep_time = RETRY_BACKOFF_BASE ** attempt
                logger.info("Retrying in %ds...", sleep_time)
                time.sleep(sleep_time)

    raise RuntimeError(f"Could not parse reference:\n{reference}") from last_error


def csv_value(value):
    """Convert Python objects into CSV-friendly strings."""
    if value is None:
        return ""
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def count_existing_rows(output_path: Path, delimiter: str = ";") -> int:
    """Return the number of data rows already written to output_path (0 if none)."""
    if not output_path.exists():
        return 0
    with output_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        rows = sum(1 for _ in reader)
    return max(rows - 1, 0)  # subtract header row


def process_csv(
    input_path: Path,
    output_path: Path,
    input_column: str,
    max_rows: int | None,
    resume: bool = False,
):
    client = build_client(BASE_URL, TIMEOUT)

    already_done = count_existing_rows(output_path) if resume else 0
    if resume and already_done:
        logger.info(
            "Resuming: %d rows already in %s, skipping them.",
            already_done,
            output_path,
        )
    elif resume:
        logger.info("Resume requested but no existing output found; starting fresh.")

    with input_path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile, delimiter=";")
        output_fields = list(reader.fieldnames) + list(
            BibliographicRecord.model_fields.keys()
        )

        # Skip rows we've already processed in a prior run.
        for _ in range(already_done):
            next(reader, None)

        mode = "a" if (resume and already_done) else "w"
        with output_path.open(mode, encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_fields, delimiter=";")
            if mode == "w":
                writer.writeheader()

            for i, row in enumerate(reader, start=already_done + 1):
                if max_rows is not None and i > max_rows:
                    break

                reference = (row.get(input_column) or "").strip()

                if reference:
                    try:
                        parsed = parse_reference(client, reference)
                    except Exception as e:
                        logger.warning("Row %d failed after retries: %s", i, e)
                        parsed = BibliographicRecord()
                else:
                    parsed = BibliographicRecord()

                out_row = row.copy()
                for key, value in parsed.model_dump().items():
                    out_row[key] = csv_value(value)

                writer.writerow(out_row)

                # Persist immediately so a crash/kill mid-run doesn't lose
                # rows sitting in a buffer, and so --resume sees them.
                outfile.flush()
                os.fsync(outfile.fileno())

                logger.info("Processed row %d", i)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_CSV,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_CSV,
    )

    parser.add_argument(
        "--column",
        default=INPUT_COLUMN,
    )

    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Only process the first N rows (useful for testing).",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue from where the output CSV left off instead of overwriting it.",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    process_csv(
        input_path=args.input,
        output_path=args.output,
        input_column=args.column,
        max_rows=args.max_rows,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()

"""Usage:
    First run:
        python structure.py --input data/raw/transkription_3_pro.csv --output data/processed/structured_sample200.csv --column Titel

    Resume after a stop/crash:
        python structure.py --input data/raw/transkription_3_pro.csv --output data/processed/structured_sample200.csv --column Titel --resume
"""