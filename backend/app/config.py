
import os
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parents[2]
ENV_FILE = BASE / "backend" / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=True)

DATABASE_URL = os.getenv("DATABASE_URL", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def resolve_path(value, default):
    path = Path(value) if value else default
    if not path.is_absolute():
        path = BASE / path
    return path.resolve()

CHROMA_PATH = resolve_path(
    os.getenv("CHROMA_PATH"),
    BASE / "data" / "chroma"
)

UPLOAD_DIR = resolve_path(
    os.getenv("UPLOAD_DIR"),
    BASE / "data" / "uploads"
)
