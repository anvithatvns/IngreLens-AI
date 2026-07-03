"""
IngreLens AI — SQLite persistence layer.

Provides local persistence for user memory, personalization, scan/analysis
history, product-analysis caching and lightweight usage analytics.

Design notes:
- Stdlib-only (sqlite3), no new dependency required.
- One short-lived connection per operation (WAL mode) — safe for Streamlit's
  multi-threaded script reruns without needing a connection pool.
- Every public function catches its own errors, logs them, and returns a
  safe default (None / False / []) instead of raising — so a DB hiccup
  never crashes a Streamlit page.
- This module is purely additive: it does not import from, or alter,
  anything in backend/services (classification / OCR / MCP / agent logic).
"""
from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

DB_PATH = Path(settings.SQLITE_DB_PATH)
UID_FILE = DB_PATH.parent / ".ingrelens_uid"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_connection():
    """Yield a short-lived SQLite connection with sane defaults, always closed."""
    conn = sqlite3.connect(str(DB_PATH), timeout=5, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> bool:
    """Create the database file and all tables if they don't already exist."""
    from backend.db.schema import SCHEMA_STATEMENTS
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with get_connection() as conn:
            for stmt in SCHEMA_STATEMENTS:
                conn.execute(stmt)
        logger.info(f"SQLite database ready at {DB_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database: {e}")
        return False


# ── Users ──────────────────────────────────────────────────────────────────
def get_or_create_local_user(name: str = "Guest") -> str:
    """
    This app has no auth, so we maintain a single persistent local identity:
    a UUID cached in a dotfile next to the database. Reused across restarts
    and browser sessions so preferences/history survive both.
    """
    try:
        if UID_FILE.exists():
            user_id = UID_FILE.read_text().strip()
            if user_id:
                _touch_user(user_id, name)
                return user_id
    except Exception as e:
        logger.warning(f"Could not read local user id file: {e}")

    user_id = str(uuid.uuid4())
    try:
        UID_FILE.parent.mkdir(parents=True, exist_ok=True)
        UID_FILE.write_text(user_id)
    except Exception as e:
        logger.warning(f"Could not persist local user id file: {e}")
    _touch_user(user_id, name)
    return user_id


def _touch_user(user_id: str, name: str = "Guest") -> None:
    try:
        with get_connection() as conn:
            now = _now()
            conn.execute(
                """INSERT INTO users (user_id, name, created_at, last_active)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET last_active=excluded.last_active""",
                (user_id, name, now, now),
            )
    except Exception as e:
        logger.error(f"Failed to upsert user {user_id}: {e}")


# ── User preferences ─────────────────────────────────────────────────────────
def save_user_preferences(user_id: str, diet_type: str = "", allergies=None,
                           preferred_language: str = "English") -> bool:
    allergies_json = json.dumps(allergies or [])
    try:
        with get_connection() as conn:
            now = _now()
            conn.execute(
                """INSERT INTO user_preferences
                       (user_id, diet_type, allergies, preferred_language, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       diet_type=excluded.diet_type,
                       allergies=excluded.allergies,
                       preferred_language=excluded.preferred_language,
                       updated_at=excluded.updated_at""",
                (user_id, diet_type, allergies_json, preferred_language, now, now),
            )
        return True
    except Exception as e:
        logger.error(f"Failed to save preferences for {user_id}: {e}")
        return False


def get_user_preferences(user_id: str) -> Optional[dict]:
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["allergies"] = json.loads(d.get("allergies") or "[]")
        return d
    except Exception as e:
        logger.error(f"Failed to load preferences for {user_id}: {e}")
        return None


# ── Serialization helpers for AnalysisResult dataclasses ────────────────────
def _serialize_result(result: Any) -> Optional[str]:
    if result is None:
        return None
    try:
        if is_dataclass(result):
            return json.dumps(asdict(result))
        if isinstance(result, dict):
            return json.dumps(result)
    except Exception as e:
        logger.warning(f"Could not serialize analysis result: {e}")
    return None


def deserialize_result(ai_response: Optional[str]):
    """Rebuild an AnalysisResult dataclass from cached JSON, if possible."""
    if not ai_response:
        return None
    try:
        from backend.services.analysis_service import AnalysisResult, IngredientResult
        data = json.loads(ai_response)
        ingredient_results = [
            IngredientResult(**ir) for ir in data.get("ingredient_results", [])
        ]
        data = {**data, "ingredient_results": ingredient_results}
        return AnalysisResult(**data)
    except Exception as e:
        logger.warning(f"Could not deserialize cached analysis result: {e}")
        return None


# ── Scan + analysis history ─────────────────────────────────────────────────
def record_scan_and_analysis(user_id: str, product_name: str, ingredients: str,
                              result: Any, barcode: str = None, image_hash: str = None) -> Optional[int]:
    """
    Persist one successful scan: a scan_history row plus its linked
    analysis_history row (AI reasoning), and refresh the product_cache.
    Returns the new scan_id, or None on failure.
    """
    classification = getattr(result, "overall_vegan", None) or getattr(result, "diet_category", None)
    confidence = getattr(result, "vegan_confidence", None)
    reasoning = getattr(result, "reasoning", "") or ""
    ai_summary = "; ".join(getattr(result, "recommendations", []) or [])
    ai_response = _serialize_result(result)

    scan_id = None
    try:
        with get_connection() as conn:
            now = _now()
            cur = conn.execute(
                """INSERT INTO scan_history
                       (user_id, product_name, barcode, image_hash, classification, confidence, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, product_name, barcode, image_hash, classification, confidence, now),
            )
            scan_id = cur.lastrowid
            conn.execute(
                """INSERT INTO analysis_history (scan_id, ingredients, reasoning, ai_summary, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (scan_id, ingredients, reasoning, ai_summary, now),
            )
    except Exception as e:
        logger.error(f"Failed to record scan/analysis for {product_name!r}: {e}")
        return None

    upsert_product_cache(barcode=barcode, image_hash=image_hash, product_name=product_name,
                          ingredients=ingredients, classification=classification, ai_response=ai_response)
    return scan_id


def get_scan_history(user_id: str, limit: int = 100) -> list:
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT s.*, a.ingredients AS full_ingredients, a.reasoning, a.ai_summary
                   FROM scan_history s
                   LEFT JOIN analysis_history a ON a.scan_id = s.scan_id
                   WHERE s.user_id = ?
                   ORDER BY s.scan_id DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to load scan history for {user_id}: {e}")
        return []


# ── Product cache (avoids repeat OCR / LLM / classification work) ───────────
def get_cached_product(barcode: str = None, image_hash: str = None) -> Optional[dict]:
    if not barcode and not image_hash:
        return None
    try:
        with get_connection() as conn:
            row = None
            if barcode:
                row = conn.execute(
                    "SELECT * FROM product_cache WHERE barcode = ?", (barcode,)
                ).fetchone()
            if row is None and image_hash:
                row = conn.execute(
                    "SELECT * FROM product_cache WHERE image_hash = ?", (image_hash,)
                ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Failed to read product cache (barcode={barcode}, image_hash={image_hash}): {e}")
        return None


def upsert_product_cache(barcode: str = None, image_hash: str = None, product_name: str = "",
                          ingredients: str = "", classification: str = "", ai_response: str = None) -> bool:
    if not barcode and not image_hash:
        return False
    try:
        with get_connection() as conn:
            now = _now()
            existing = None
            if barcode:
                existing = conn.execute(
                    "SELECT rowid FROM product_cache WHERE barcode = ?", (barcode,)
                ).fetchone()
            if existing is None and image_hash:
                existing = conn.execute(
                    "SELECT rowid FROM product_cache WHERE image_hash = ?", (image_hash,)
                ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE product_cache SET product_name=?, ingredients=?, classification=?,
                           ai_response=?, last_updated=?, barcode=COALESCE(barcode, ?), image_hash=COALESCE(image_hash, ?)
                       WHERE rowid = ?""",
                    (product_name, ingredients, classification, ai_response, now,
                     barcode, image_hash, existing["rowid"]),
                )
            else:
                conn.execute(
                    """INSERT INTO product_cache
                           (barcode, image_hash, product_name, ingredients, classification, ai_response, last_updated)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (barcode, image_hash, product_name, ingredients, classification, ai_response, now),
                )
        return True
    except Exception as e:
        logger.error(f"Failed to upsert product cache (barcode={barcode}, image_hash={image_hash}): {e}")
        return False


# ── User activity / analytics ───────────────────────────────────────────────
def log_activity(user_id: str, action: str, page: str = "") -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO user_activity (user_id, action, page, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, action, page, _now()),
            )
        return True
    except Exception as e:
        logger.error(f"Failed to log activity {action!r} for {user_id}: {e}")
        return False
