"""Application paths and model configuration."""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "assessments.db"
CHECKPOINT_PATH = DATA_DIR / "checkpoints.sqlite"
LOG_PATH = DATA_DIR / "agent.log"

# Local LLM configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)