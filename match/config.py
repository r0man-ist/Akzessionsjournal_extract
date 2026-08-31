# ============================================================================
# --- CONFIGURATION ----------------------------------------------------------
# ============================================================================



# OpenRouter
BASE_URL = "https://openrouter.ai/api/v1"

# LLM
MODEL            = "qwen/qwen3.8-27b"
MODEL_SHORT_NAME = "qwen3.8-27b"

REASONING = {"effort": "none"} # none, low, minimal

TEMPERATURE = 0.0
MAX_TOKENS = 4096

# API
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2
TIMEOUT = 60