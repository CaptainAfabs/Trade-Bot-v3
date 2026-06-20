-- Stock Advisor schema. Single-user but structured for future multi-user.
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    display_name  TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS profiles (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    risk                TEXT NOT NULL CHECK (risk IN ('low','medium','high')),
    timeline            TEXT NOT NULL CHECK (timeline IN ('short','medium','long','generational')),
    capital_usd         REAL NOT NULL DEFAULT 500,
    min_market_cap_usd  REAL NOT NULL DEFAULT 0,
    max_position_pct    REAL NOT NULL DEFAULT 10,
    max_sector_pct      REAL NOT NULL DEFAULT 30,
    sectors_exclude     TEXT DEFAULT '[]',          -- JSON list
    sectors_prefer      TEXT DEFAULT '[]',          -- JSON list
    dividend_only       INTEGER DEFAULT 0,
    esg_only            INTEGER DEFAULT 0,
    follow_investors    TEXT DEFAULT '[]',          -- JSON list of investor slugs
    is_default          INTEGER DEFAULT 0,
    created_at          TEXT DEFAULT (datetime('now')),
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS holdings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id    INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticker        TEXT NOT NULL,
    shares        REAL NOT NULL,
    avg_cost_usd  REAL NOT NULL,
    opened_at     TEXT DEFAULT (datetime('now')),
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS watchlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id  INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticker      TEXT NOT NULL,
    added_at    TEXT DEFAULT (datetime('now')),
    UNIQUE (profile_id, ticker)
);

CREATE TABLE IF NOT EXISTS investors (
    slug          TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('fund','politician','individual')),
    cik           TEXT,
    bio           TEXT,
    photo_url     TEXT,
    description   TEXT,
    is_seeded     INTEGER DEFAULT 1,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS investor_holdings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    investor     TEXT NOT NULL REFERENCES investors(slug) ON DELETE CASCADE,
    period       TEXT NOT NULL,                     -- '2026Q1' etc.
    ticker       TEXT NOT NULL,
    shares       REAL,
    value_usd    REAL,
    pct_portfolio REAL,
    change_pct   REAL,                              -- vs prior period
    filed_at     TEXT,
    UNIQUE (investor, period, ticker)
);

CREATE TABLE IF NOT EXISTS news_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT NOT NULL,
    url          TEXT UNIQUE NOT NULL,
    title        TEXT NOT NULL,
    summary      TEXT,
    published_at TEXT,
    tickers      TEXT DEFAULT '[]',                 -- JSON list
    sentiment    REAL,                              -- -1..1
    impact       INTEGER,                           -- 0..5
    fetched_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id  INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content     TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trade_journal (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id      INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticker          TEXT NOT NULL,
    action          TEXT NOT NULL CHECK (action IN ('buy','sell','hold','watch')),
    thesis          TEXT,
    bot_score       REAL,
    user_rating     INTEGER,                        -- 1..5 thumbs feedback
    outcome_pct     REAL,                           -- filled in later
    decided_at      TEXT DEFAULT (datetime('now')),
    reviewed_at     TEXT
);

CREATE TABLE IF NOT EXISTS quant_cache (
    ticker       TEXT NOT NULL,
    metric       TEXT NOT NULL,
    value        REAL,
    as_of        TEXT NOT NULL,
    fetched_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (ticker, metric, as_of)
);
