"""
run.py

Runs the OCR prompt over a directory of page images, cleans each response,
stitches all pages into a single validated CSV.

Usage:
    python run.py
"""

import csv
import io
import re
from pathlib import Path

import pandas as pd


import ocr.config as config 
from ocr.prompts import build_prompt
from ocr.openrouter_client import transcribe_page


def find_page_images(input_dir: Path) -> list[Path]:
    """Return page image paths sorted by filename (assumed to encode page order)."""
    pages = [
        p for p in input_dir.iterdir()
        if p.suffix.lower() in config.IMAGE_EXTENSIONS
    ]
    return sorted(pages)


def strip_code_fences(text: str) -> str:
    """Remove ```tsv/```csv fences or stray commentary the model might add."""
    text = text.strip()
    text = re.sub(r"^```(?:tsv|csv)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_csv_response(raw_text: str, source_page: str) -> pd.DataFrame:
    """
    Parses one page's raw TSV response into a DataFrame, aligned to
    config.CSV_COLUMNS. Drops the model's own header row if present.
    """
    cleaned = strip_code_fences(raw_text)
    reader = csv.reader(io.StringIO(cleaned), delimiter="\t")
    rows = [r for r in reader if any(cell.strip() for cell in r)]

    if not rows:
        return pd.DataFrame(columns=config.CSV_COLUMNS)

    first_row_lower = [c.strip().lower() for c in rows[0]]
    if first_row_lower[:2] == ["accession_no", "date"]:
        rows = rows[1:]

    df = pd.DataFrame(rows)

    expected_n = len(config.CSV_COLUMNS)
    if df.shape[1] < expected_n:
        for i in range(df.shape[1], expected_n):
            df[i] = ""
    elif df.shape[1] > expected_n:
        df = df.iloc[:, :expected_n]

    df.columns = config.CSV_COLUMNS

    df["source_page"] = df["source_page"].replace("", source_page)
    df["source_page"] = df["source_page"].fillna(source_page)

    return df


def validate(df: pd.DataFrame) -> None:
    """
    Sanity checks on the stitched CSV. Prints warnings; does not raise,
    so a full run always produces output for manual review.
    """
    numeric_acc = pd.to_numeric(df["accession_no"], errors="coerce")

    # Duplicate accession numbers (e.g. from overlapping page scans).
    dupes = df[numeric_acc.duplicated(keep=False) & numeric_acc.notna()]
    if not dupes.empty:
        print(f"[WARN] {len(dupes)} rows share a duplicated accession_no:")
        print(dupes[["accession_no", "source_page", "row_confidence"]].to_string(index=False))

    # Gaps in the accession number sequence.
    valid_nums = sorted(numeric_acc.dropna().unique())
    gaps = []
    for a, b in zip(valid_nums, valid_nums[1:]):
        if b - a > 1:
            gaps.append((a, b))
    if gaps:
        print(f"[WARN] Possible gaps in accession_no sequence: {gaps}")




def run_pipeline() -> pd.DataFrame:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.RAW_RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

    pages = find_page_images(config.INPUT_DIR)
    if not pages:
        raise RuntimeError(f"No page images found in {config.INPUT_DIR}")

    all_dfs = []

    for page_path in pages:
        source_page = page_path.name
        raw_out_path = config.RAW_RESPONSES_DIR / f"{page_path.stem}.txt"

        if raw_out_path.exists():
            print(f"Skipping {source_page} (raw response already exists, using cached result) ...")
            raw_response = raw_out_path.read_text(encoding="utf-8")
        else:
            print(f"Processing {source_page} ...")
            prompt_text = build_prompt(source_page=source_page)
            raw_response = transcribe_page(page_path, prompt_text)
            raw_out_path.write_text(raw_response, encoding="utf-8")

        page_df = parse_csv_response(raw_response, source_page)
        all_dfs.append(page_df)

    combined = pd.concat(all_dfs, ignore_index=True)
    validate(combined)

    combined.to_csv(config.COMBINED_CSV_PATH, index=False, encoding="utf-8")
    print(f"Wrote combined CSV: {config.COMBINED_CSV_PATH}")

    return combined


if __name__ == "__main__":
    run_pipeline()