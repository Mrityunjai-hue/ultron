"""
ULTRON Memory Database v2.0 — Long-Term Episodic Memory & Dynamic Relationship Matrix
─────────────────────────────────────────────────────────────────────────────
Features:
- Persistent SQLite schema with users, conversations, relationships, facts, scenes
- Dynamic Relationship Matrix: STRANGER → OBSERVED → ASSOCIATE → SYNCHRONIZED
- Trust Score & Interaction Frequency Analytics
- Full Conversation History & Fact Retrieval for LLM context injection
- Biometric Face Template & Metadata persistence
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import asyncio
import sqlite3
import json
import logging
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger("ultron.memory.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    face_embedding BLOB,
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
    trust_score REAL DEFAULT 0.0,
    preference_context TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    fact_key TEXT NOT NULL,
    fact_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
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
"""

class MemoryDB:
    """Persistent SQLite Memory Subsystem for ULTRON."""

    def __init__(self, config: dict):
        self.db_path = config.get("memory", {}).get("db_path", "data/memory.db")
        # Ensure path is relative to project root or workspace
        if not os.path.isabs(self.db_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, self.db_path)
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(SCHEMA)
        logger.info(f"Memory DB initialized at: {self.db_path}")

    # ── Interaction & Relationship Logging ───────────────────────────────── #

    async def log_interaction(self, user_id: Optional[str], user_said: str, ultron_said: str, mood: str = "calm", scene: str = ""):
        await asyncio.to_thread(self._sync_log, user_id, user_said, ultron_said, mood, scene)

    def _sync_log(self, user_id: Optional[str], user_said: str, ultron_said: str, mood: str, scene: str):
        with self._connect() as conn:
            uid = None
            if user_id and user_id.upper() != "UNKNOWN":
                # Ensure user exists
                row = conn.execute("SELECT id FROM users WHERE name=?", (user_id,)).fetchone()
                if row:
                    uid = row["id"]
                else:
                    cur = conn.execute("INSERT INTO users (name, last_seen, recognition_count) VALUES (?, CURRENT_TIMESTAMP, 1)", (user_id,))
                    uid = cur.lastrowid

            # Insert conversation record
            conn.execute(
                "INSERT INTO conversations (user_id, user_said, ultron_said, mood, scene_context) VALUES (?,?,?,?,?)",
                (uid, user_said, ultron_said, mood, json.dumps({"description": scene}))
            )

            # Update Relationship & Evolution Matrix
            if uid:
                rel_row = conn.execute("SELECT interaction_count, trust_score FROM user_relationships WHERE user_id=?", (uid,)).fetchone()
                if rel_row:
                    count = rel_row["interaction_count"] + 1
                else:
                    count = 1

                # Calculate evolved relationship tier
                # STRANGER (0-2) -> OBSERVED (3-9) -> ASSOCIATE (10-24) -> SYNCHRONIZED (25+)
                if count >= 25:
                    mode = "SYNCHRONIZED"
                elif count >= 10:
                    mode = "ASSOCIATE"
                elif count >= 3:
                    mode = "OBSERVED"
                else:
                    mode = "STRANGER"

                trust = min(1.0, round(count * 0.04, 2))

                conn.execute("""
                    INSERT INTO user_relationships (user_id, relationship_mode, interaction_count, last_interaction, trust_score)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        relationship_mode = excluded.relationship_mode,
                        interaction_count = excluded.interaction_count,
                        last_interaction  = excluded.last_interaction,
                        trust_score       = excluded.trust_score
                """, (uid, mode, count, trust))

                conn.execute("UPDATE users SET last_seen=CURRENT_TIMESTAMP WHERE id=?", (uid,))
                logger.info(f"Updated relationship for user {user_id}: {mode} (Count: {count}, Trust: {trust:.2f})")

    # ── User Context & History Retrieval ─────────────────────────────────── #

    async def get_relationship(self, name: str) -> dict:
        return await asyncio.to_thread(self._sync_get_rel, name)

    def _sync_get_rel(self, name: str) -> dict:
        with self._connect() as conn:
            row = conn.execute("""
                SELECT ur.*, u.last_seen FROM user_relationships ur
                JOIN users u ON u.id = ur.user_id
                WHERE u.name = ?
            """, (name,)).fetchone()
            if row:
                return dict(row)
            return {"relationship_mode": "STRANGER", "interaction_count": 0, "trust_score": 0.0, "last_seen": "never"}

    async def get_recent_history(self, name: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._sync_get_history, name, limit)

    def _sync_get_history(self, name: Optional[str], limit: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if name and name.upper() != "UNKNOWN":
                rows = conn.execute("""
                    SELECT c.user_said, c.ultron_said, c.mood, c.timestamp
                    FROM conversations c
                    JOIN users u ON u.id = c.user_id
                    WHERE u.name = ?
                    ORDER BY c.id DESC LIMIT ?
                """, (name, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT user_said, ultron_said, mood, timestamp
                    FROM conversations
                    ORDER BY id DESC LIMIT ?
                """, (limit,)).fetchall()
            return [dict(r) for r in reversed(rows)]

    async def remember_fact(self, name: str, key: str, value: str):
        await asyncio.to_thread(self._sync_remember_fact, name, key, value)

    def _sync_remember_fact(self, name: str, key: str, value: str):
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM users WHERE name=?", (name,)).fetchone()
            if not row:
                cur = conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
                uid = cur.lastrowid
            else:
                uid = row["id"]
            conn.execute("INSERT INTO facts (user_id, fact_key, fact_value) VALUES (?,?,?)", (uid, key, value))
            logger.info(f"Saved fact for {name}: {key} = {value}")

    async def get_facts(self, name: str) -> Dict[str, str]:
        return await asyncio.to_thread(self._sync_get_facts, name)

    def _sync_get_facts(self, name: str) -> Dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT f.fact_key, f.fact_value
                FROM facts f
                JOIN users u ON u.id = f.user_id
                WHERE u.name = ?
            """, (name,)).fetchall()
            return {r["fact_key"]: r["fact_value"] for r in rows}

    async def get_full_context(self, name: Optional[str]) -> Dict[str, Any]:
        """Provides structured context bundle for LLM system prompt."""
        if not name or name.upper() == "UNKNOWN":
            return {
                "name": None,
                "relationship_mode": "STRANGER",
                "interaction_count": 0,
                "trust_score": 0.0,
                "last_seen": "never",
                "recent_history": await self.get_recent_history(None, limit=3),
                "facts": {}
            }

        rel = await self.get_relationship(name)
        history = await self.get_recent_history(name, limit=4)
        facts = await self.get_facts(name)

        return {
            "name": name,
            "relationship_mode": rel.get("relationship_mode", "STRANGER"),
            "interaction_count": rel.get("interaction_count", 0),
            "trust_score": rel.get("trust_score", 0.0),
            "last_seen": str(rel.get("last_seen") or "recently"),
            "recent_history": history,
            "facts": facts
        }

    # ── Biometrics & Face Storage ────────────────────────────────────────── #

    async def save_face_template(self, name: str, embedding_bytes: bytes, metadata: Optional[dict] = None) -> bool:
        return await asyncio.to_thread(self._sync_save_face, name, embedding_bytes, metadata)

    def _sync_save_face(self, name: str, embedding_bytes: bytes, metadata: Optional[dict]) -> bool:
        meta_json = json.dumps(metadata or {})
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO users (name, face_embedding, face_metadata, last_seen, recognition_count)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1)
                ON CONFLICT(name) DO UPDATE SET
                    face_embedding = excluded.face_embedding,
                    face_metadata  = excluded.face_metadata,
                    last_seen      = CURRENT_TIMESTAMP
            """, (name, embedding_bytes, meta_json))
        logger.info(f"Face template persisted in SQLite for subject: {name}")
        return True

    async def get_all_face_templates(self) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._sync_get_all_faces)

    def _sync_get_all_faces(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, name, face_embedding, face_metadata FROM users WHERE face_embedding IS NOT NULL").fetchall()
            return [dict(r) for r in rows]

    async def record_recognition(self, name: str):
        await asyncio.to_thread(self._sync_record_rec, name)

    def _sync_record_rec(self, name: str):
        with self._connect() as conn:
            conn.execute("UPDATE users SET recognition_count = recognition_count + 1, last_seen = CURRENT_TIMESTAMP WHERE name=?", (name,))

    async def forget_user(self, name: str):
        await asyncio.to_thread(self._sync_forget, name)

    def _sync_forget(self, name: str):
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM users WHERE name=?", (name,)).fetchone()
            if row:
                uid = row["id"]
                conn.execute("DELETE FROM facts WHERE user_id=?", (uid,))
                conn.execute("DELETE FROM conversations WHERE user_id=?", (uid,))
                conn.execute("DELETE FROM user_relationships WHERE user_id=?", (uid,))
                conn.execute("DELETE FROM users WHERE id=?", (uid,))
                logger.info(f"Purged record and all related memory for: {name}")

    async def search_memory(self, query: str, user: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches conversation history and facts matching keywords."""
        return await asyncio.to_thread(self._sync_search_memory, query, user, limit)

    def _sync_search_memory(self, query: str, user: Optional[str], limit: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            pattern = f"%{query.strip()}%"
            results = []

            # 1. Search conversations
            if user and user.upper() != "UNKNOWN":
                c_rows = conn.execute("""
                    SELECT c.user_said, c.ultron_said, c.timestamp
                    FROM conversations c
                    JOIN users u ON u.id = c.user_id
                    WHERE u.name = ? AND (c.user_said LIKE ? OR c.ultron_said LIKE ?)
                    ORDER BY c.id DESC LIMIT ?
                """, (user, pattern, pattern, limit)).fetchall()
            else:
                c_rows = conn.execute("""
                    SELECT user_said, ultron_said, timestamp
                    FROM conversations
                    WHERE user_said LIKE ? OR ultron_said LIKE ?
                    ORDER BY id DESC LIMIT ?
                """, (pattern, pattern, limit)).fetchall()

            for r in c_rows:
                results.append({
                    "type": "conversation",
                    "user_said": r["user_said"],
                    "ultron_said": r["ultron_said"],
                    "timestamp": r["timestamp"],
                })

            # 2. Search facts
            if user and user.upper() != "UNKNOWN":
                f_rows = conn.execute("""
                    SELECT f.fact_key, f.fact_value
                    FROM facts f
                    JOIN users u ON u.id = f.user_id
                    WHERE u.name = ? AND (f.fact_key LIKE ? OR f.fact_value LIKE ?)
                    LIMIT ?
                """, (user, pattern, pattern, limit)).fetchall()
            else:
                f_rows = conn.execute("""
                    SELECT fact_key, fact_value FROM facts
                    WHERE fact_key LIKE ? OR fact_value LIKE ?
                    LIMIT ?
                """, (pattern, pattern, limit)).fetchall()

            for r in f_rows:
                results.append({
                    "type": "fact",
                    "key": r["fact_key"],
                    "value": r["fact_value"],
                })

            return results[:limit]
