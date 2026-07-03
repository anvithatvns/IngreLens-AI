"""
IngreLens AI — SQLite schema definitions.

Six tables supporting user memory, personalization, history, caching and
analytics. All DDL is idempotent (CREATE TABLE IF NOT EXISTS) so the database
is created automatically on first run and left untouched on every subsequent
run.
"""

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id     TEXT PRIMARY KEY,
        name        TEXT,
        created_at  TEXT NOT NULL,
        last_active TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id            TEXT PRIMARY KEY,
        diet_type          TEXT,
        allergies           TEXT,
        preferred_language TEXT,
        created_at         TEXT NOT NULL,
        updated_at         TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scan_history (
        scan_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        TEXT NOT NULL,
        product_name   TEXT,
        barcode        TEXT,
        image_hash     TEXT,
        classification TEXT,
        confidence     REAL,
        timestamp      TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_history (
        analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id     INTEGER NOT NULL,
        ingredients TEXT,
        reasoning   TEXT,
        ai_summary  TEXT,
        timestamp   TEXT NOT NULL,
        FOREIGN KEY (scan_id) REFERENCES scan_history(scan_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS product_cache (
        barcode        TEXT,
        image_hash     TEXT,
        product_name   TEXT,
        ingredients    TEXT,
        classification TEXT,
        ai_response    TEXT,
        last_updated   TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_activity (
        activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT NOT NULL,
        action      TEXT NOT NULL,
        page        TEXT,
        timestamp   TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_scan_history_user ON scan_history(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_analysis_history_scan ON analysis_history(scan_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_product_cache_barcode ON product_cache(barcode) WHERE barcode IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_product_cache_image_hash ON product_cache(image_hash) WHERE image_hash IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_user_activity_user ON user_activity(user_id)",
]
