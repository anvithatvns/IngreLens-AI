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

import hashlib
import json
import secrets
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
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
    from backend.db.schema import TABLE_STATEMENTS, COLUMN_MIGRATIONS, INDEX_STATEMENTS
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with get_connection() as conn:
            for stmt in TABLE_STATEMENTS:
                conn.execute(stmt)
            for table, column, ddl in COLUMN_MIGRATIONS:
                existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            for stmt in INDEX_STATEMENTS:
                conn.execute(stmt)
        logger.info(f"SQLite database ready at {DB_PATH}")
        _seed_demo_user()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database: {e}")
        return False


def _seed_demo_user() -> None:
    """Seed the capstone demo login: Anvitha / test123@gmail.com / test123."""
    try:
        if get_user_by_email("test123@gmail.com"):
            return
        user_id = str(uuid.uuid4())
        _touch_user(user_id, "Anvitha")
        set_password(user_id, "test123@gmail.com", "test123")
    except Exception as e:
        logger.error(f"Failed to seed demo user: {e}")


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


# ── Authentication ───────────────────────────────────────────────────────────
def _hash_password(password: str, salt: str = None) -> tuple:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return digest, salt


def get_user_by_email(email: str) -> Optional[dict]:
    try:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Failed to look up user by email {email!r}: {e}")
        return None


def create_account(name: str, email: str, password: str) -> Optional[str]:
    """Sign-up: create a new user identity with a hashed password. Returns user_id, or None if the email is taken."""
    if get_user_by_email(email):
        return None
    user_id = str(uuid.uuid4())
    _touch_user(user_id, name)
    if set_password(user_id, email, password):
        return user_id
    return None


def set_password(user_id: str, email: str, password: str) -> bool:
    digest, salt = _hash_password(password)
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET email = ?, password_hash = ?, password_salt = ? WHERE user_id = ?",
                (email, digest, salt, user_id),
            )
        return True
    except Exception as e:
        logger.error(f"Failed to set password for {user_id}: {e}")
        return False


def authenticate(email: str, password: str) -> Optional[dict]:
    """Sign-in: returns the user row on success, None on bad credentials."""
    user = get_user_by_email(email)
    if not user or not user.get("password_hash"):
        return None
    digest, _ = _hash_password(password, user.get("password_salt") or "")
    if secrets.compare_digest(digest, user["password_hash"]):
        _touch_user(user["user_id"], user.get("name") or "")
        return user
    return None


# ── User preferences ─────────────────────────────────────────────────────────
def save_user_preferences(user_id: str, diet_type: str = "", allergies=None,
                           preferred_language: str = "English", gender: str = None,
                           age: int = None, height_cm: float = None, weight_kg: float = None) -> bool:
    allergies_json = json.dumps(allergies or [])
    try:
        with get_connection() as conn:
            now = _now()
            conn.execute(
                """INSERT INTO user_preferences
                       (user_id, diet_type, allergies, preferred_language,
                        gender, age, height_cm, weight_kg, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       diet_type=excluded.diet_type,
                       allergies=excluded.allergies,
                       preferred_language=excluded.preferred_language,
                       gender=COALESCE(excluded.gender, user_preferences.gender),
                       age=COALESCE(excluded.age, user_preferences.age),
                       height_cm=COALESCE(excluded.height_cm, user_preferences.height_cm),
                       weight_kg=COALESCE(excluded.weight_kg, user_preferences.weight_kg),
                       updated_at=excluded.updated_at""",
                (user_id, diet_type, allergies_json, preferred_language,
                 gender, age, height_cm, weight_kg, now, now),
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


def compute_bmi_and_targets(gender: str, age: int, height_cm: float, weight_kg: float) -> Optional[dict]:
    """Mifflin-St Jeor BMR + moderate-activity multiplier (1.55) for a simple daily target."""
    if not (age and height_cm and weight_kg):
        return None
    try:
        bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
        if (gender or "").lower().startswith("f"):
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
        else:
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        daily_calories = round(bmr * 1.55)
        daily_protein = round(weight_kg * 0.8)
        return {"bmi": bmi, "daily_calories": daily_calories, "daily_protein": daily_protein}
    except Exception as e:
        logger.error(f"Failed to compute BMI/targets: {e}")
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


# ── Consumption tracking (for the daily-intake checker) ─────────────────────
def log_consumption(user_id: str, product_name: str, calories: float = 0,
                     protein: float = 0, fat: float = 0, sugar: float = 0) -> bool:
    try:
        with get_connection() as conn:
            now = _now()
            conn.execute(
                """INSERT INTO consumption_log
                       (user_id, product_name, calories, protein, fat, sugar, log_date, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, product_name, calories or 0, protein or 0, fat or 0, sugar or 0,
                 date.today().isoformat(), now),
            )
        return True
    except Exception as e:
        logger.error(f"Failed to log consumption for {user_id}: {e}")
        return False


def get_daily_consumption(user_id: str, log_date: str = None) -> dict:
    log_date = log_date or date.today().isoformat()
    try:
        with get_connection() as conn:
            row = conn.execute(
                """SELECT COALESCE(SUM(calories),0) AS calories, COALESCE(SUM(protein),0) AS protein,
                          COALESCE(SUM(fat),0) AS fat, COALESCE(SUM(sugar),0) AS sugar
                   FROM consumption_log WHERE user_id = ? AND log_date = ?""",
                (user_id, log_date),
            ).fetchone()
        return dict(row) if row else {"calories": 0, "protein": 0, "fat": 0, "sugar": 0}
    except Exception as e:
        logger.error(f"Failed to load daily consumption for {user_id}: {e}")
        return {"calories": 0, "protein": 0, "fat": 0, "sugar": 0}
