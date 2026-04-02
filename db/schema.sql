PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS markets (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    category TEXT NOT NULL,
    market_price REAL NOT NULL,
    resolution_date TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    outcome INTEGER,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    market_id TEXT NOT NULL REFERENCES markets(id),
    action TEXT NOT NULL,
    entry_price REAL NOT NULL,
    position_size REAL NOT NULL,
    predicted_probability REAL NOT NULL,
    edge REAL NOT NULL,
    kelly_fraction REAL NOT NULL,
    timestamp TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    pnl REAL,
    failure_category TEXT
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    bankroll REAL NOT NULL,
    open_position_count INTEGER NOT NULL,
    total_trades INTEGER NOT NULL,
    win_rate REAL NOT NULL,
    total_pnl REAL NOT NULL,
    current_drawdown REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS research_cache (
    market_id TEXT PRIMARY KEY REFERENCES markets(id),
    report_json TEXT NOT NULL,
    gathered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS predictions (
    id TEXT PRIMARY KEY,
    market_id TEXT NOT NULL REFERENCES markets(id),
    source TEXT NOT NULL,
    probability REAL NOT NULL,
    confidence REAL NOT NULL,
    reasoning TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    insight TEXT NOT NULL,
    trade_id TEXT REFERENCES trades(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calibration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    predicted_probability REAL NOT NULL,
    actual_outcome INTEGER NOT NULL,
    trade_id TEXT REFERENCES trades(id),
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trades_market_id ON trades(market_id);
CREATE INDEX IF NOT EXISTS idx_trades_resolved ON trades(resolved);
CREATE INDEX IF NOT EXISTS idx_markets_resolved ON markets(resolved);
CREATE INDEX IF NOT EXISTS idx_calibration_log_timestamp ON calibration_log(timestamp);

-- API key / config storage (values entered via the Settings page)
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    is_secret INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

-- Pipeline run history for health monitoring
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    error_message TEXT,
    markets_processed INTEGER NOT NULL DEFAULT 0,
    trades_executed INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started ON pipeline_runs(started_at);
