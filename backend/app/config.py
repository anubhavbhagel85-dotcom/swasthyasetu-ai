"""
Central configuration for SwasthyaSetu AI backend.
All values can be overridden via environment variables (see .env.example).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# --- App metadata ---
APP_NAME = "SwasthyaSetu AI"
APP_VERSION = "1.0.0"

# --- CORS ---
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# --- Retrieval settings ---
# Minimum similarity score (0-1) for a knowledge-base entry to be considered a match.
RETRIEVAL_THRESHOLD = float(os.getenv("RETRIEVAL_THRESHOLD", "0.08"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "2"))

# --- Optional: Bhashini API (voice + Indic translation), used only by the
# bonus voice flow. The core text flow works fully offline without these. ---
BHASHINI_USER_ID = os.getenv("BHASHINI_USER_ID", "")
BHASHINI_API_KEY = os.getenv("BHASHINI_API_KEY", "")
BHASHINI_PIPELINE_ID = os.getenv("BHASHINI_PIPELINE_ID", "")
BHASHINI_ENABLED = bool(BHASHINI_USER_ID and BHASHINI_API_KEY)

# --- Optional: LLM for natural-language phrasing of the final answer. ---
# The safety layer and source retrieval NEVER depend on this — if it's absent,
# the app still returns fully correct, cited guidance using template phrasing.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_ENABLED = bool(ANTHROPIC_API_KEY)
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
