"""
IngreLens AI — Configuration Management
Handles all env vars, feature flags, and constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

class Settings:
    # ── App ───────────────────────────────────────────────
    APP_NAME: str = "IngreLens AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered ingredient intelligence platform"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── AI Provider ───────────────────────────────────────
    # Free tier: uses local models + Open Food Facts API
    # Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable LLM features
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    USE_LLM: bool = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai | anthropic
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")   # cheapest capable model
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    # ── Vector DB (ChromaDB — free, local) ────────────────
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "vector_store" / "chroma_db")
    CHROMA_COLLECTION: str = "ingredients_kb"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"   # free, local Sentence Transformer

    # ── Relational DB (SQLite — local persistence) ────────
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "ingrelens.db"))

    # ── Knowledge Base ────────────────────────────────────
    KB_PATH: str = str(BASE_DIR / "knowledge_base" / "ingredients.json")

    # ── External APIs (all free tier) ────────────────────
    OPENFOODFACTS_BASE: str = "https://world.openfoodfacts.org"
    OPENFOODFACTS_SEARCH: str = "https://world.openfoodfacts.org/cgi/search.pl"
    OFF_USER_AGENT: str = "IngreLensAI/1.0 (github.com/ingrelens-ai)"

    # ── Logging ───────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

    # ── Feature flags ─────────────────────────────────────
    ENABLE_OCR: bool = os.getenv("ENABLE_OCR", "true").lower() == "true"
    ENABLE_RAG: bool = os.getenv("ENABLE_RAG", "true").lower() == "true"
    ENABLE_BARCODE: bool = os.getenv("ENABLE_BARCODE", "true").lower() == "true"

    # ── Allergens tracked ────────────────────────────────
    TRACKED_ALLERGENS: list = [
        "dairy", "eggs", "gluten", "soy", "peanuts", "tree nuts",
        "shellfish", "fish", "sesame", "wheat"
    ]

    # ── Health flags ──────────────────────────────────────
    ULTRA_PROCESSED_MARKERS: list = [
        "high fructose corn syrup", "artificial flavor", "artificial colour",
        "artificial color", "sodium nitrate", "sodium nitrite",
        "modified starch", "hydrogenated", "maltodextrin"
    ]

    PRESERVATIVE_MARKERS: list = [
        "sodium benzoate", "potassium sorbate", "calcium propionate",
        "sodium propionate", "BHA", "BHT", "TBHQ"
    ]


settings = Settings()
