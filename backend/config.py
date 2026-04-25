from pathlib import Path
import os
import json
import logging

from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
FAISS_DIR = STORAGE_DIR / "faiss_indices"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
FAISS_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = BASE_DIR / "classroom.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
TOP_K = int(os.getenv("TOP_K", "4"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# --- Firebase Configuration ---
# Option 1: Service account JSON file path
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")

# Option 2: Service account JSON as environment variable (for Hugging Face Spaces / Docker)
FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")


def get_firebase_credentials():
    """Return parsed service account dict or None."""
    if FIREBASE_SERVICE_ACCOUNT_PATH and Path(FIREBASE_SERVICE_ACCOUNT_PATH).exists():
        with open(FIREBASE_SERVICE_ACCOUNT_PATH, "r") as f:
            return json.load(f)
    if FIREBASE_SERVICE_ACCOUNT_JSON:
        try:
            return json.loads(FIREBASE_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError:
            logger.error("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON")
            return None
    return None
