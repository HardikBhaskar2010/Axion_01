"""Storage layer - SQLite with in-memory cache"""
import aiosqlite
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
from app.models import Session, Action, LogEntry
from app.config import settings

class Storage:
    """Hybrid storage with SQLite persistence and in-memory cache"""
    
    def __init__(self):
        self.db_path = settings.db_path
        self.mode = settings.storage_mode
        
        # In-memory cache
        self.sessions: Dict[str, Session] = {}
        self.actions: Dict[str, Action] = {}
        self.logs: Dict[str, List[LogEntry]] = {}  # session_id -> logs
        self.settings_cache: Dict[str, Any] = {
            "root_path": settings.sandbox_path,
            "first_run": True
        }
        
    async def init_db(self):
        """Initialize SQLite database"""
        if self.mode != "sqlite":
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    allowed_scopes TEXT NOT NULL,
                    expires_in_minutes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    root_path TEXT
                )
            """)
            
            # Actions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id TEXT PRIMARY KEY,
                    tool TEXT NOT NULL,
                    args TEXT NOT NULL,
                    need_approval INTEGER NOT NULL,
                    reason_brief TEXT,
                    risk TEXT NOT NULL,
                    session_id TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # Logs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    action_id TEXT PRIMARY KEY,
                    tool TEXT NOT NULL,
                    args TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    result TEXT,
                    error TEXT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL
                )
            """)
            
            # Settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            await db.commit()
            
        # Load settings from DB
        await self.load_settings()
    
    async def load_settings(self):
        """Load settings from database"""
        if self.mode != "sqlite":
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT key, value FROM settings") as cursor:
                async for row in cursor:
                    key, value = row
                    try:
                        self.settings_cache[key] = json.loads(value)
                    except:
                        self.settings_cache[key] = value
    
    async def save_setting(self, key: str, value: Any):
        """Save a setting"""
        self.settings_cache[key] = value
        
        if self.mode == "sqlite":
            async with aiosqlite.connect(self.db_path) as db:
                value_str = json.dumps(value) if not isinstance(value, str) else value
                await db.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (key, value_str)
                )
                await db.commit()
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting"""
        return self.settings_cache.get(key, default)
    
    async def save_session(self, session: Session):
        """Save session"""
        self.sessions[session.id] = session
        
        if self.mode == "sqlite":
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO sessions 
                    (id, mode, allowed_scopes, expires_in_minutes, created_at, root_path)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        session.id,
                        session.mode,
                        json.dumps(session.allowed_scopes),
                        session.expires_in_minutes,
                        session.created_at.isoformat(),
                        session.root_path
                    )
                )
                await db.commit()
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session"""
        return self.sessions.get(session_id)
    
    async def save_action(self, action: Action):
        """Save action"""
        self.actions[action.id] = action
        
        if self.mode == "sqlite":
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO actions 
                    (id, tool, args, need_approval, reason_brief, risk, session_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        action.id,
                        action.tool,
                        json.dumps(action.args),
                        1 if action.need_approval else 0,
                        action.reason_brief,
                        action.risk,
                        action.session_id,
                        action.timestamp.isoformat()
                    )
                )
                await db.commit()
    
    async def get_action(self, action_id: str) -> Optional[Action]:
        """Get action"""
        return self.actions.get(action_id)
    
    async def delete_action(self, action_id: str):
        """Delete action after approval/denial"""
        if action_id in self.actions:
            del self.actions[action_id]
    
    async def save_log(self, log: LogEntry):
        """Save log entry"""
        if log.session_id not in self.logs:
            self.logs[log.session_id] = []
        self.logs[log.session_id].append(log)
        
        if self.mode == "sqlite":
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO logs 
                    (action_id, tool, args, success, result, error, timestamp, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        log.action_id,
                        log.tool,
                        json.dumps(log.args),
                        1 if log.success else 0,
                        json.dumps(log.result) if log.result else None,
                        log.error,
                        log.timestamp.isoformat(),
                        log.session_id
                    )
                )
                await db.commit()
    
    async def get_logs(self, session_id: str) -> List[LogEntry]:
        """Get logs for session"""
        return self.logs.get(session_id, [])

# Global storage instance
storage = Storage()