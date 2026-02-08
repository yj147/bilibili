-- Bili-Sentinel Database Schema (SQLite)

-- Accounts table: stores Bilibili credentials
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    uid INTEGER,
    sessdata TEXT NOT NULL,
    bili_jct TEXT NOT NULL,
    buvid3 TEXT,
    group_tag TEXT DEFAULT 'default',
    is_active BOOLEAN DEFAULT 1,
    last_check_at DATETIME,
    status TEXT DEFAULT 'unknown',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Targets table: stores report targets (videos, comments, users)
CREATE TABLE IF NOT EXISTS targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('video', 'comment', 'user')),
    identifier TEXT NOT NULL,
    aid INTEGER,
    reason_id INTEGER,
    reason_text TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    retry_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

-- Report logs: detailed execution records
CREATE TABLE IF NOT EXISTS report_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER REFERENCES targets(id) ON DELETE CASCADE,
    account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    request_data TEXT,
    response_data TEXT,
    success BOOLEAN,
    error_message TEXT,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Auto-reply configuration
CREATE TABLE IF NOT EXISTS autoreply_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT,
    response TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1
);

-- Scheduled tasks
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    cron_expression TEXT,
    interval_seconds INTEGER,
    is_active BOOLEAN DEFAULT 1,
    last_run_at DATETIME,
    next_run_at DATETIME,
    config_json TEXT
);

-- System configuration (key-value store)
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Default config values
INSERT OR IGNORE INTO system_config (key, value) VALUES ('min_delay', '2.0');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('max_delay', '10.0');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('ua_rotation', 'true');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('auto_clean_logs', 'true');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('log_retention_days', '30');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('webhook_url', '');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('notify_level', 'error');

-- Auto-reply state (dedup tracking)
CREATE TABLE IF NOT EXISTS autoreply_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    talker_id INTEGER NOT NULL,
    last_msg_ts INTEGER DEFAULT 0,
    UNIQUE(account_id, talker_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_targets_status ON targets(status);
CREATE INDEX IF NOT EXISTS idx_targets_type ON targets(type);
CREATE INDEX IF NOT EXISTS idx_report_logs_target ON report_logs(target_id);
CREATE INDEX IF NOT EXISTS idx_report_logs_account ON report_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_accounts_active ON accounts(is_active);
