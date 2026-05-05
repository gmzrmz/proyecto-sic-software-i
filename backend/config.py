import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

INSTANCE_NAME = os.getenv("INSTANCE_NAME", "local")
DATA_SOURCE = os.getenv("DATA_SOURCE", "synthetic")
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR.parent / "data" / "cloudsense.db"))

COLLECT_INTERVAL_MINUTES = int(os.getenv("COLLECT_INTERVAL_MINUTES", "5"))

THRESHOLD_CPU = float(os.getenv("THRESHOLD_CPU", "85"))
THRESHOLD_RAM = float(os.getenv("THRESHOLD_RAM", "85"))

# LLM - provider-agnostic; set LLM_PROVIDER to "openai", "anthropic",
# "openrouter", "ollama", etc. The llm/ module reads these at runtime.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
NARRATIVE_INTERVAL_MINUTES = int(os.getenv("NARRATIVE_INTERVAL_MINUTES", "60"))
