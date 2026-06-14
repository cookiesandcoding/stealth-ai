import asyncpg
import logging
import sqlite3
import json
import uuid
import re
import os
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.is_sqlite: bool = False

    async def connect(self):
        if self.pool or self.sqlite_conn:
            return

        try:
            logger.info("Attempting to connect to PostgreSQL...")
            self.pool = await asyncpg.create_pool(
                dsn=settings.DATABASE_URL,
                min_size=5,
                max_size=20,
                max_inactive_connection_lifetime=300.0
            )
            logger.info("Successfully established connection pool to PostgreSQL.")
            self.is_sqlite = False
        except Exception as e:
            logger.warning(f"Failed to create PostgreSQL connection pool: {e}. Falling back to persistent local SQLite...")
            self.pool = None
            self.is_sqlite = True
            
            # Determine path for SQLite file in backend root
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "local_copilot.db"
            )
            logger.info(f"Initializing local SQLite database at {db_path}...")
            
            # Connect with thread safety checks off because we use to_thread and serialize connections
            self.sqlite_conn = sqlite3.connect(db_path, check_same_thread=False)
            self.sqlite_conn.row_factory = sqlite3.Row
            
            # Register helper functions to match PostgreSQL behaviors
            def gen_random_uuid_fn():
                return str(uuid.uuid4())
            def now_fn():
                return datetime.utcnow().isoformat()
                
            self.sqlite_conn.create_function("gen_random_uuid", 0, gen_random_uuid_fn)
            self.sqlite_conn.create_function("now", 0, now_fn)
            self.sqlite_conn.create_function("NOW", 0, now_fn)
            
            # Initialize schema tables
            self._init_sqlite_schema()
            logger.info("Local SQLite database initialized successfully with schema.")

    def _init_sqlite_schema(self):
        cursor = self.sqlite_conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            name TEXT,
            subscription TEXT DEFAULT 'free',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            file_name TEXT,
            file_url TEXT,
            parsed_text TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT DEFAULT 'Interview Session',
            transcript TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            category TEXT,
            confidence REAL,
            question_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id TEXT PRIMARY KEY,
            question_id TEXT,
            ai_response TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id TEXT PRIMARY KEY,
            session_id TEXT UNIQUE,
            filler_words_count TEXT,
            speaking_pace REAL,
            clarity_score REAL,
            knowledge_gaps TEXT,
            suggestions TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        """)
        self.sqlite_conn.commit()

    def _translate_query(self, query: str) -> str:
        # Convert PostgreSQL params ($1, $2, etc.) into SQLite (?)
        return re.sub(r'\$\d+', '?', query)

    def _serialize_args(self, args: tuple) -> list:
        # Convert compound parameters (lists, dicts) to JSON strings for SQLite storage
        res = []
        for arg in args:
            if isinstance(arg, (list, dict)):
                res.append(json.dumps(arg))
            else:
                res.append(arg)
        return res

    def _deserialize_row(self, row: Any) -> Dict[str, Any]:
        if not row:
            return {}
        d = dict(row)
        # Parse fields that are stored as JSON in SQLite but returned as lists/dicts
        for key in ["filler_words_count", "knowledge_gaps", "suggestions"]:
            if key in d and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        return d

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Closed PostgreSQL connection pool.")
        if self.sqlite_conn:
            self.sqlite_conn.close()
            self.sqlite_conn = None
            logger.info("Closed SQLite connection.")

    async def fetch_rows(self, query: str, *args) -> List[Dict[str, Any]]:
        if not self.is_sqlite:
            if not self.pool:
                raise RuntimeError("Database pool is not connected.")
            async with self.pool.acquire() as conn:
                records = await conn.fetch(query, *args)
                return [dict(r) for r in records]
        else:
            if not self.sqlite_conn:
                raise RuntimeError("SQLite database is not connected.")
            
            def run_query():
                translated = self._translate_query(query)
                serialized = self._serialize_args(args)
                cursor = self.sqlite_conn.cursor()
                cursor.execute(translated, serialized)
                rows = cursor.fetchall()
                return [self._deserialize_row(r) for r in rows]
                
            return await asyncio.to_thread(run_query)

    async def fetch_row(self, query: str, *args) -> Optional[Dict[str, Any]]:
        if not self.is_sqlite:
            if not self.pool:
                raise RuntimeError("Database pool is not connected.")
            async with self.pool.acquire() as conn:
                record = await conn.fetchrow(query, *args)
                return dict(record) if record else None
        else:
            if not self.sqlite_conn:
                raise RuntimeError("SQLite database is not connected.")
                
            def run_query():
                translated = self._translate_query(query)
                serialized = self._serialize_args(args)
                cursor = self.sqlite_conn.cursor()
                cursor.execute(translated, serialized)
                row = cursor.fetchone()
                return self._deserialize_row(row) if row else None
                
            return await asyncio.to_thread(run_query)

    async def execute(self, query: str, *args) -> str:
        if not self.is_sqlite:
            if not self.pool:
                raise RuntimeError("Database pool is not connected.")
            async with self.pool.acquire() as conn:
                return await conn.execute(query, *args)
        else:
            if not self.sqlite_conn:
                raise RuntimeError("SQLite database is not connected.")
                
            def run_query():
                translated = self._translate_query(query)
                serialized = self._serialize_args(args)
                cursor = self.sqlite_conn.cursor()
                cursor.execute(translated, serialized)
                self.sqlite_conn.commit()
                return "SUCCESS"
                
            return await asyncio.to_thread(run_query)

db = Database()

