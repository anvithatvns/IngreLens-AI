"""
IngreLens AI — SQLite schema definitions.

Tables supporting user memory, personalization, history, caching, analytics,
auth and daily-intake tracking. All DDL is idempotent (CREATE TABLE IF NOT
EXISTS) so the database is created automatically on first run and left
untouched on every subsequent run. TABLE_STATEMENTS must run, then
COLUMN_MIGRATIONS (for DBs created before a column existed), then
INDEX_STATEMENTS — some indexes reference columns only guaranteed to exist
after migration.
"""

TABLE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id       TEXT PRIMARY KEY,
        name          TEXT,
        email         TEXT,
        password_hash TEXT,
        password_salt TEXT,
        created_at    TEXT NOT NULL,
        last_active   TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id            TEXT PRIMARY KEY,
        diet_type          TEXT,
        allergies           TEXT,
        preferred_language TEXT,
        gender             TEXT,
        age                INTEGER,
        height_cm          REAL,
        weight_kg          REAL,
        created_at         TEXT NOT NULL,
        updated_at         TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS consumption_log (
        log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      TEXT NOT NULL,
        product_name TEXT,
        calories     REAL DEFAULT 0,
        protein      REAL DEFAULT 0,
        fat          REAL DEFAULT 0,
        sugar        REAL DEFAULT 0,
        quantity     REAL,
        unit         TEXT,
        log_date     TEXT NOT NULL,
        timestamp    TEXT NOT NULL,
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
]

# (table, column, column_ddl) — applied to DBs created before a given column
# existed, since CREATE TABLE IF NOT EXISTS alone won't alter an existing table.
COLUMN_MIGRATIONS = [
    ("users", "email", "TEXT"),
    ("users", "password_hash", "TEXT"),
    ("users", "password_salt", "TEXT"),
    ("user_preferences", "gender", "TEXT"),
    ("user_preferences", "age", "INTEGER"),
    ("user_preferences", "height_cm", "REAL"),
    ("user_preferences", "weight_kg", "REAL"),
    ("consumption_log", "quantity", "REAL"),
    ("consumption_log", "unit", "TEXT"),
    ("user_preferences", "diet_modes", "TEXT"),
]

INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_scan_history_user ON scan_history(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_analysis_history_scan ON analysis_history(scan_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_product_cache_barcode ON product_cache(barcode) WHERE barcode IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_product_cache_image_hash ON product_cache(image_hash) WHERE image_hash IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_user_activity_user ON user_activity(user_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_consumption_user_date ON consumption_log(user_id, log_date)",
]

# Kept for backward compatibility with any external caller expecting the old name.
SCHEMA_STATEMENTS = TABLE_STATEMENTS + INDEX_STATEMENTS
