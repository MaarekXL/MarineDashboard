SCHEMA_VERSION = 2


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    timestamp TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,

    source TEXT NOT NULL,
    valid INTEGER NOT NULL DEFAULT 1,

    speed_knots REAL,
    course_deg REAL,
    altitude_m REAL,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_positions_timestamp
ON positions(timestamp);


CREATE TABLE IF NOT EXISTS tide_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    target_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    height_m REAL NOT NULL,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(target_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_tide_points_target_time
ON tide_points(target_id, timestamp);


CREATE TABLE IF NOT EXISTS tide_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    target_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,

    event_type TEXT NOT NULL,
    height_m REAL NOT NULL,

    coefficient INTEGER,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(
        target_id,
        timestamp,
        event_type
    )
);

CREATE INDEX IF NOT EXISTS idx_tide_events_target_time
ON tide_events(target_id, timestamp);
"""