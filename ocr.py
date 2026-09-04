"""
ocr.py

Runs the OCR prompt over a directory of page images, calls the LLM with a
structured output schema, stitches all pages into a single validated CSV.

Usage:
    python ocr.py
"""

from pathlib import Path

import pandas as pd

import ocr.config as config
from ocr.models import OcrEntry, OcrPage
from ocr.prompts import build_prompt
from ocr.openrouter_client import transcribe_page
from utils.iiif import find_manifest, load_iiif_canvas_map


def ocr_page_to_df(page: OcrPage, source_image: str, source_url: str = "") -> pd.DataFrame:
    """Convert an OcrPage object into a DataFrame aligned to OcrEntry fields."""
    columns = list(OcrEntry.model_fields.keys()) + ["page_number", "source_image", "source_url"]

    if page.is_empty or not page.entries:
        return pd.DataFrame(columns=columns)

    rows = []
    for entry in page.entries:
        row = entry.model_dump()
        row["page_number"] = page.page_number
        row["source_image"] = source_image
        row["source_url"] = source_url
        rows.append(row)

    return pd.DataFrame(rows)


def validate(df: pd.DataFrame) -> None:
    if "accession_no" not in df.columns:
        print("[WARN] 'accession_no' column not found in output — skipping validation.")
        return

    numeric_acc = pd.to_numeric(df["accession_no"], errors="coerce")

    dupes = df[numeric_acc.duplicated(keep=False) & numeric_acc.notna()]
    if not dupes.empty:
        print(f"[WARN] {len(dupes)} rows share a duplicated accession_no:")
        print(dupes[["accession_no", "source_image", "row_confidence"]].to_string(index=False))

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

    pages = sorted(
        p for p in config.INPUT_DIR.iterdir()
        if p.suffix.lower() in config.IMAGE_EXTENSIONS
    )
    if not pages:
        raise RuntimeError(f"No page images found in {config.INPUT_DIR}")

    canvas_map: dict[int, str] = {}
    manifest_path = find_manifest(config.INPUT_DIR)
    if manifest_path:
        canvas_map = load_iiif_canvas_map(manifest_path)
        print(f"Loaded IIIF manifest: {len(canvas_map)} canvases mapped.")

    all_dfs = []

    for page_path in pages:
        source_image = page_path.name
        cache_path = config.RAW_RESPONSES_DIR / f"{page_path.stem}.json"

        try:
            source_url = canvas_map.get(int(page_path.stem), "")
        except ValueError:
            source_url = ""

        if cache_path.exists():
            print(f"Skipping {source_image} (cached) ...")
            page = OcrPage.model_validate_json(cache_path.read_text(encoding="utf-8"))
        else:
            print(f"Processing {source_image} ...")
            prompt_text = build_prompt(source_page=source_image)
            page = transcribe_page(page_path, prompt_text)
            cache_path.write_text(page.model_dump_json(indent=2), encoding="utf-8")

        all_dfs.append(ocr_page_to_df(page, source_image, source_url))

    combined = pd.concat(all_dfs, ignore_index=True)
    validate(combined)

    combined.to_csv(config.COMBINED_CSV_PATH, index=False, encoding="utf-8")
    print(f"Wrote combined CSV: {config.COMBINED_CSV_PATH}")

    return combined


if __name__ == "__main__":
    run_pipeline()