"""Backend settings. Everything can be overridden with environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# SQLite file used during the prototype stage (README: Technology Stack -> Database).
DB_PATH = Path(os.environ.get("FINSIGHT_DB", BASE_DIR / "finsight.db"))

# Frontend origins allowed to call the API (Vite dev server by default).
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("FINSIGHT_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # per uploaded file
