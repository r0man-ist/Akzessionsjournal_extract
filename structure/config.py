# ============================================================================
# --- CONFIGURATION ----------------------------------------------------------
# ============================================================================
import os

from dotenv import load_dotenv

load_dotenv()

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

# LLM
MODEL            = "qwen/qwen3.8-27b"
MODEL_SHORT_NAME = "qwen3.8-27b"

TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS  = 1024

REASONING = {"effort": "none"} # low, minimal

# API
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2
TIMEOUT = 60

# Input / Output
INPUT_CSV  = "data/raw/transkription_3_pro_sample200.csv"
OUTPUT_CSV = "data/processed/structured_sample200.csv"

# Column containing the bibliographic string
INPUT_COLUMN = "Titel"

# Processing
BATCH_SIZE = 20