import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project Directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"

# Ensure crucial directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Model Configurations
CLASSIFIER_MODEL = "gemini-3.5-flash"
EMBEDDING_MODEL = "gemini-embedding-001"
GENERATION_MODEL = "gemini-3.5-flash"

# RAG Configurations
TOP_K = 3

# Escalation Rules & Thresholds
# ChromaDB yields distances. For cosine distance, similarity can be computed as: 1.0 - (distance)
# This threshold defines the minimum required similarity score.
CONFIDENCE_THRESHOLD = 0.45

# Number of consecutive turns the user can remain in a frustrated state before auto-escalation
FRUSTRATION_LIMIT = 2

# Sensitive topics/keywords that trigger immediate human escalation
SENSITIVE_KEYWORDS = [
    "billing",
    "refund",
    "legal",
    "lawsuit",
    "sue",
    "attorney",
    "court",
    "hack",
    "breach",
    "compromised",
    "unauthorized charge",
    "duplicate charge",
    "account ownership",
    "stolen password",
    "identity theft"
]
