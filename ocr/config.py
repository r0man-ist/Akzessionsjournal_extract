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
TEMPERATURE = 0.0
MAX_TOKENS  = 8000
REASONING   = {"effort": "minimal"}

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_ROOT / "../data/images/sample_3"      # page images go here
OUTPUT_DIR = PROJECT_ROOT / "../data/raw"
RAW_RESPONSES_DIR = OUTPUT_DIR / "raw_responses"  # per-page raw LLM output, for debugging
COMBINED_CSV_PATH = OUTPUT_DIR / "combined.csv"



# Accepted image extensions when scanning INPUT_DIR
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}