-- ULTRON Memory Schema v2.0

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    face_embedding BLOB NOT NULL,
    face_metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP,
    recognition_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    user_said TEXT NOT NULL,
    ultron_said TEXT NOT NULL,
    mood TEXT,
    scene_context TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_relationships (
    user_id INTEGER PRIMARY KEY,
    relationship_mode TEXT DEFAULT 'STRANGER',
    interaction_count INTEGER DEFAULT 0,
    last_interaction TIMESTAMP,
    average_mood TEXT,
    preference_context TEXT,
    trust_score REAL DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS conversation_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,
    tag TEXT NOT NULL,
    confidence REAL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
