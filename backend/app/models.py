"""Data models"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
import uuid

class ParseResult(BaseModel):
    """Result from command parser"""
    intent: str
    args: Dict[str, Any]
    confidence: float
    source: Literal["rules", "llm"]

class Action(BaseModel):
    """Proposed action"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool: str
    args: Dict[str, Any]
    need_approval: bool
    reason_brief: str
    risk: Literal["low", "medium", "high"]
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ActionResult(BaseModel):
    """Result of action execution"""
    action_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class Session(BaseModel):
    """User session"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: Literal["paranoid", "normal", "hands_free"]
    allowed_scopes: List[str]
    expires_in_minutes: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    root_path: str = ""

class LogEntry(BaseModel):
    """Action log entry"""
    action_id: str
    tool: str
    args: Dict[str, Any]
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str

class SessionStartRequest(BaseModel):
    mode: Literal["paranoid", "normal", "hands_free"] = "normal"

class PlanRequest(BaseModel):
    session_id: str
    utterance: str

class ApprovalRequest(BaseModel):
    action_id: str
    decision: Literal["allow", "deny"]

class PrivilegeRequest(BaseModel):
    need: List[str]
    target_path: str
    expires_minutes: int = 15
    reason_brief: str

class RootPathRequest(BaseModel):
    path: str