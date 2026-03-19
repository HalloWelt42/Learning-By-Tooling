"""db.py -- Datenbankschicht Learn-e-Versum"""

import sqlite3, json, os
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).parent / "lbt.db")))


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def row_to_dict(row) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    for key in ("tags", "related_cards", "card_ids", "category_codes",
                "category_filter", "document_ids"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except Exception:
                d[key] = []
    return d


def init_db():
    conn = get_db()
    conn.executescript("""

    -- Benutzer
    CREATE TABLE IF NOT EXISTS users (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        email          TEXT    NOT NULL UNIQUE,
        password_hash  TEXT    NOT NULL,
        display_name   TEXT    NOT NULL DEFAULT '',
        is_admin       INTEGER NOT NULL DEFAULT 0,
        disabled       INTEGER NOT NULL DEFAULT 0,
        created_at     TEXT    DEFAULT (datetime('now'))
    );

    -- Pakete (Themenwelten)
    CREATE TABLE IF NOT EXISTS packages (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        description TEXT,
        color       TEXT    NOT NULL DEFAULT '#2196F3',
        icon        TEXT    NOT NULL DEFAULT 'fa-graduation-cap',
        created_at  TEXT    DEFAULT (datetime('now')),
        updated_at  TEXT    DEFAULT (datetime('now'))
    );

    -- Kategorien
    CREATE TABLE IF NOT EXISTS categories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT    NOT NULL UNIQUE,
        name        TEXT    NOT NULL,
        description TEXT,
        color       TEXT    DEFAULT '#5b8aff',
        icon        TEXT    DEFAULT 'fa-layer-group',
        created_at  TEXT    DEFAULT (datetime('now'))
    );

    -- Karten
    CREATE TABLE IF NOT EXISTS cards (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id       TEXT    NOT NULL,
        package_id    INTEGER,
        category_code TEXT    NOT NULL,
        question      TEXT    NOT NULL,
        answer        TEXT    NOT NULL,
        hint          TEXT,
        tags          TEXT    DEFAULT '[]',
        difficulty    INTEGER DEFAULT 2,
        active        INTEGER DEFAULT 1,
        created_at    TEXT    DEFAULT (datetime('now')),
        updated_at    TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY (package_id)    REFERENCES packages(id),
        FOREIGN KEY (category_code) REFERENCES categories(code),
        UNIQUE(card_id, package_id)
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
        card_id, question, answer, hint, tags,
        content='cards', content_rowid='id'
    );

    -- Karten-Statistik pro Benutzer (SRS)
    CREATE TABLE IF NOT EXISTS card_stats (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER NOT NULL DEFAULT 1,
        card_id        TEXT    NOT NULL,
        times_shown    INTEGER DEFAULT 0,
        times_correct  INTEGER DEFAULT 0,
        times_wrong    INTEGER DEFAULT 0,
        last_reviewed  TEXT,
        streak         INTEGER DEFAULT 0,
        ease_factor    REAL    DEFAULT 2.5,
        interval_days  INTEGER DEFAULT 1,
        due_date       TEXT,
        UNIQUE(user_id, card_id)
    );

    -- Sessions pro Benutzer
    CREATE TABLE IF NOT EXISTS sessions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL DEFAULT 1,
        started_at      TEXT    DEFAULT (datetime('now')),
        ended_at        TEXT,
        mode            TEXT    DEFAULT 'standard',
        package_id      INTEGER,
        category_filter TEXT    DEFAULT '[]',
        total_cards     INTEGER DEFAULT 0,
        correct         INTEGER DEFAULT 0,
        skipped         INTEGER DEFAULT 0,
        FOREIGN KEY (package_id) REFERENCES packages(id)
    );

    -- Reviews pro Benutzer
    CREATE TABLE IF NOT EXISTS reviews (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL DEFAULT 1,
        session_id  INTEGER,
        card_id     TEXT    NOT NULL,
        result      TEXT    NOT NULL,
        user_answer TEXT,
        ai_score    REAL,
        ai_feedback TEXT,
        reviewed_at TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );

    -- Dokumente
    CREATE TABLE IF NOT EXISTS documents (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        package_id    INTEGER,
        filename      TEXT    NOT NULL,
        title         TEXT    NOT NULL,
        filetype      TEXT    NOT NULL,
        filesize      INTEGER DEFAULT 0,
        chunk_count   INTEGER DEFAULT 0,
        card_count    INTEGER DEFAULT 0,
        status        TEXT    DEFAULT 'uploaded',
        created_at    TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY (package_id) REFERENCES packages(id)
    );

    -- Dokument-Chunks
    CREATE TABLE IF NOT EXISTS document_chunks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        text        TEXT    NOT NULL,
        processed   INTEGER DEFAULT 0,
        FOREIGN KEY (document_id) REFERENCES documents(id)
    );

    -- Karten-Entwürfe
    CREATE TABLE IF NOT EXISTS card_drafts (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id   INTEGER,
        package_id    INTEGER,
        chunk_id      INTEGER,
        category_code TEXT    NOT NULL DEFAULT 'GB',
        question      TEXT    NOT NULL,
        answer        TEXT    NOT NULL,
        hint          TEXT,
        difficulty    INTEGER DEFAULT 2,
        status        TEXT    DEFAULT 'pending',
        created_at    TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (package_id)  REFERENCES packages(id)
    );

    -- Lernpfade
    CREATE TABLE IF NOT EXISTS learning_paths (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        package_id  INTEGER NOT NULL,
        name        TEXT    NOT NULL,
        description TEXT,
        sort_order  INTEGER DEFAULT 0,
        created_at  TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY (package_id) REFERENCES packages(id)
    );

    -- Kapitel innerhalb eines Lernpfads
    CREATE TABLE IF NOT EXISTS path_chapters (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        path_id        INTEGER NOT NULL,
        sort_order     INTEGER DEFAULT 0,
        title          TEXT    NOT NULL,
        description    TEXT,
        document_ids   TEXT    DEFAULT '[]',
        card_ids       TEXT    DEFAULT '[]',
        pass_threshold REAL    DEFAULT 0.7,
        FOREIGN KEY (path_id) REFERENCES learning_paths(id)
    );

    -- Lexikon
    CREATE TABLE IF NOT EXISTS lexicon (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        package_id    INTEGER,
        term          TEXT    NOT NULL UNIQUE,
        definition    TEXT    NOT NULL,
        category_code TEXT,
        related_cards TEXT    DEFAULT '[]',
        created_at    TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY (package_id) REFERENCES packages(id)
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS lexicon_fts USING fts5(
        term, definition,
        content='lexicon', content_rowid='id'
    );

    -- KI-generierte Multiple-Choice-Optionen (Cache)
    CREATE TABLE IF NOT EXISTS mc_options (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id    TEXT    NOT NULL,
        package_id INTEGER,
        options    TEXT    NOT NULL DEFAULT '[]',
        created_at TEXT    DEFAULT (datetime('now')),
        expires_at TEXT,
        UNIQUE(card_id, package_id)
    );

    -- Paket-Zuordnung pro Benutzer
    CREATE TABLE IF NOT EXISTS user_packages (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        package_id INTEGER NOT NULL,
        role       TEXT    NOT NULL DEFAULT 'learner',
        created_at TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY (user_id)    REFERENCES users(id),
        FOREIGN KEY (package_id) REFERENCES packages(id),
        UNIQUE(user_id, package_id)
    );

    """)
    conn.commit()
    _migrate(conn)
    _seed(conn)
    conn.close()



def _migrate(conn: sqlite3.Connection):
    """Schema-Migration: fehlende Spalten und Tabellen ergänzen."""
    existing_tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    # users Tabelle (Upgrade von Einzelnutzer-Version)
    if 'users' not in existing_tables:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                email          TEXT    NOT NULL UNIQUE,
                password_hash  TEXT    NOT NULL,
                display_name   TEXT    NOT NULL DEFAULT '',
                created_at     TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

    # packages Tabelle (falls fehlt - Upgrade von v1.x)
    if 'packages' not in existing_tables:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS packages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                description TEXT,
                color       TEXT    NOT NULL DEFAULT '#2196F3',
                icon        TEXT    NOT NULL DEFAULT 'fa-graduation-cap',
                created_at  TEXT    DEFAULT (datetime('now')),
                updated_at  TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

    # users: is_admin Spalte ergänzen falls fehlt
    if 'users' in existing_tables:
        user_cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if 'is_admin' not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
            conn.execute("UPDATE users SET is_admin=1 WHERE id=1")
            conn.commit()
        if 'disabled' not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0")
            conn.commit()

    # cards: package_id Spalte ergänzen falls fehlt
    card_cols = {r[1] for r in conn.execute("PRAGMA table_info(cards)").fetchall()}
    if 'package_id' not in card_cols:
        conn.execute("ALTER TABLE cards ADD COLUMN package_id INTEGER")
        conn.commit()

    # sessions: user_id und package_id
    sess_cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    if 'package_id' not in sess_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN package_id INTEGER")
        conn.commit()
    if 'user_id' not in sess_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
        conn.commit()
    if 'card_order' not in sess_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN card_order TEXT DEFAULT '[]'")
        conn.commit()
    if 'current_index' not in sess_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN current_index INTEGER DEFAULT 0")
        conn.commit()

    # reviews: user_id, time_ms
    if 'reviews' in existing_tables:
        rev_cols = {r[1] for r in conn.execute("PRAGMA table_info(reviews)").fetchall()}
        if 'user_id' not in rev_cols:
            conn.execute("ALTER TABLE reviews ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            conn.commit()
        if 'time_ms' not in rev_cols:
            conn.execute("ALTER TABLE reviews ADD COLUMN time_ms INTEGER DEFAULT 0")
            conn.commit()

    # card_stats: user_id, avg_quality, avg_time_ms
    if 'card_stats' in existing_tables:
        stat_cols = {r[1] for r in conn.execute("PRAGMA table_info(card_stats)").fetchall()}
        if 'user_id' not in stat_cols:
            conn.execute("ALTER TABLE card_stats ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            conn.commit()
        if 'ease_factor' not in stat_cols:
            conn.execute("ALTER TABLE card_stats ADD COLUMN ease_factor REAL DEFAULT 2.5")
            conn.commit()
        if 'interval_days' not in stat_cols:
            conn.execute("ALTER TABLE card_stats ADD COLUMN interval_days INTEGER DEFAULT 1")
            conn.commit()
        if 'avg_quality' not in stat_cols:
            conn.execute("ALTER TABLE card_stats ADD COLUMN avg_quality REAL DEFAULT 0.0")
            conn.commit()
        if 'avg_time_ms' not in stat_cols:
            conn.execute("ALTER TABLE card_stats ADD COLUMN avg_time_ms INTEGER DEFAULT 0")
            conn.commit()

    # documents: package_id
    if 'documents' in existing_tables:
        doc_cols = {r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()}
        if 'package_id' not in doc_cols:
            conn.execute("ALTER TABLE documents ADD COLUMN package_id INTEGER")
            conn.commit()

    # card_drafts: package_id
    if 'card_drafts' in existing_tables:
        draft_cols = {r[1] for r in conn.execute("PRAGMA table_info(card_drafts)").fetchall()}
        if 'package_id' not in draft_cols:
            conn.execute("ALTER TABLE card_drafts ADD COLUMN package_id INTEGER")
            conn.commit()

    # learning_paths: package_id
    if 'learning_paths' in existing_tables:
        path_cols = {r[1] for r in conn.execute("PRAGMA table_info(learning_paths)").fetchall()}
        if 'package_id' not in path_cols:
            conn.execute("ALTER TABLE learning_paths ADD COLUMN package_id INTEGER")
            conn.commit()

    # lexicon: package_id
    if 'lexicon' in existing_tables:
        lex_cols = {r[1] for r in conn.execute("PRAGMA table_info(lexicon)").fetchall()}
        if 'package_id' not in lex_cols:
            conn.execute("ALTER TABLE lexicon ADD COLUMN package_id INTEGER")
            conn.commit()

    # user_packages: Sicherstellen dass jeder User alle Pakete sieht
    if 'user_packages' in existing_tables:
        conn.execute("""
            INSERT OR IGNORE INTO user_packages (user_id, package_id, role)
            SELECT u.id, p.id, 'owner'
            FROM users u, packages p
            WHERE NOT EXISTS (
                SELECT 1 FROM user_packages up WHERE up.user_id=u.id AND up.package_id=p.id
            )
        """)
        conn.commit()

    # cards: UNIQUE(card_id) -> UNIQUE(card_id, package_id) Migration
    # Prüfe ob der alte globale UNIQUE-Index noch existiert
    if 'cards' in existing_tables:
        indexes = conn.execute("PRAGMA index_list(cards)").fetchall()
        has_old_unique = any(
            idx[1] == 'sqlite_autoindex_cards_1' or
            (idx[2] == 1 and len(conn.execute(f"PRAGMA index_info({idx[1]})").fetchall()) == 1)
            for idx in indexes
        )
        if has_old_unique:
            try:
                conn.execute("DROP INDEX IF EXISTS sqlite_autoindex_cards_1")
            except Exception:
                pass
            # Neuen zusammengesetzten Index erstellen
            try:
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_pkg_cardid ON cards(card_id, package_id)")
                conn.commit()
            except Exception:
                pass

    # Kategorie-Namen: Umlaute korrigieren (falls alte ASCII-Version in DB)
    umlaut_fixes = [
        ("GS", "Geschaeftsprozesse", "Geschaeftsprozesse und Anwendungsfaelle"),
        ("FE", "Fehler",            "Fehlerbehandlung und Debugging"),
    ]
    for code, name, desc in umlaut_fixes:
        conn.execute(
            "UPDATE categories SET name=?, description=? WHERE code=? AND (name LIKE '%ae%' OR name LIKE '%ue%' OR name NOT LIKE '%ae%')",
            (name, desc, code)
        )
    conn.commit()


def _seed(conn: sqlite3.Connection):
    """Standardkategorien einspielen."""

    cats = [
        ("GB",  "Grundlagen",     "Definitionen, Konzepte, Fachbegriffe",     "#5b8aff", "fa-book"),
        ("TH",  "Theorie",        "Theoretisches Wissen und Zusammenhänge",   "#9b7ddf", "fa-lightbulb"),
        ("PX",  "Praxis",         "Praktische Anwendung und Übungen",         "#3dd68c", "fa-hammer"),
        ("VF",  "Verfahren",      "Abläufe, Prozesse und Methoden",           "#ff9f43", "fa-arrows-spin"),
        ("PR",  "Prüfung",        "Prüfungsrelevante Fragen",                 "#ff6b6b", "fa-clipboard-check"),
        ("VT",  "Vertiefung",     "Weiterführende und schwierige Themen",     "#40e0d0", "fa-layer-group"),
        ("AL",  "Allgemein",      "Alles was nicht in andere Kategorien passt","#6b7280", "fa-folder"),
    ]

    for code, name, desc, color, icon in cats:
        try:
            conn.execute(
                "INSERT INTO categories (code,name,description,color,icon) VALUES (?,?,?,?,?)",
                (code, name, desc, color, icon)
            )
        except Exception:
            pass
    conn.commit()
