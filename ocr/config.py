import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
# --- OpenRouter ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


# LLM
MODEL            = "google/gemini-3.1-pro-preview"
MODEL_SHORT_NAME = "gemini-3.1-pro-preview"

# Generation params
TEMPERATURE = 0.0          # deterministic transcription, not creative
MAX_TOKENS = 8000          # raise if pages have many rows

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_ROOT / "../data/images/sample"      # page images go here
OUTPUT_DIR = PROJECT_ROOT / "../data/raw"
RAW_RESPONSES_DIR = OUTPUT_DIR / "raw_responses"  # per-page raw LLM output, for debugging
COMBINED_CSV_PATH = OUTPUT_DIR / "combined.csv"

# --- CSV schema ---
# Single source of truth for column order/names — used for validation and
# for stripping/checking headers returned by the model.
CSV_COLUMNS = [
    "accession_no",
    "date",
    "letter",
    "entry_text",
    "source_note",
    "mark",
    "price",
    "fraction",
    "subject_group",
    "quantity",
    "binding_note",
    "row_confidence",
    "additional_notes",
    "source_page",
]

# Accepted image extensions when scanning INPUT_DIR
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}