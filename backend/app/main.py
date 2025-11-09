"""AI Axion - Main FastAPI Application"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from datetime import datetime, timezone
import json

from app.config import settings
from app.models import (
    Session, Action, ActionResult, LogEntry,
    SessionStartRequest, PlanRequest, ApprovalRequest,
    PrivilegeRequest, RootPathRequest
)
from app.storage import storage
from app.parser import parse
from app.tools import ToolExecutor

# WebSocket connections
ws_connections: Dict[str, WebSocket] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup"""
    await storage.init_db()
    yield
    # Cleanup on shutdown

app = FastAPI(
    title="AI Axion",
    description="Local Jarvis-Style Desktop Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_origins == "*" else settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_allowed_scopes(mode: str) -> List[str]:
    """Get allowed scopes based on mode"""
    if mode == "paranoid":
        return ["system.read"]
    elif mode == "normal":
        return ["apps.open", "system.read", "files.sandbox_rw", "browser.basic"]
    else:  # hands_free
        return ["apps.open", "system.read", "files.sandbox_rw", "browser.basic", "files.outside_sandbox"]

def assess_risk(tool: str, args: Dict) -> str:
    """Assess risk level of an action"""
    if tool.startswith("system.") and tool != "system.time":
        return "high"
    elif tool.startswith("files.") and tool in ["files.delete", "files.move"]:
        return "medium"
    elif tool.startswith("files."):
        return "medium"
    elif tool == "privilege.request":
        return "high"
    else:
        return "low"

def needs_approval(tool: str, risk: str, mode: str) -> bool:
    """Determine if action needs approval"""
    if mode == "paranoid":
        return risk in ["low", "medium", "high"]
    elif mode == "normal":
        return risk in ["medium", "high"]
    else:  # hands_free
        return risk == "high"

@app.get("/api")
async def root():
    """Health check"""
    return {"message": "Hello World"}

@app.post("/api/session/start")
async def start_session(request: SessionStartRequest):
    """Create a new session"""
    session = Session(
        mode=request.mode,
        allowed_scopes=get_allowed_scopes(request.mode),
        expires_in_minutes=settings.max_session_minutes,
        root_path=await storage.get_setting("root_path", settings.sandbox_path)
    )
    
    await storage.save_session(session)
    
    return session

@app.post("/api/plan")
async def create_plan(request: PlanRequest):
    """Parse utterance and create action plan"""
    # Get session
    session = await storage.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Parse command
    parse_result = parse(request.utterance, {"session": session})
    
    # Create actions based on intent
    actions = []
    
    if parse_result.intent == "unknown":
        # Return empty action list for unknown commands
        return {"actions": [], "auto_results": []}
    
    # Create action
    action = Action(
        tool=parse_result.intent,
        args=parse_result.args,
        need_approval=False,  # Will be determined below
        reason_brief="proposed by rules",
        risk=assess_risk(parse_result.intent, parse_result.args),
        session_id=session.id
    )
    
    # Check if needs approval
    action.need_approval = needs_approval(action.tool, action.risk, session.mode)
    
    # Save action
    await storage.save_action(action)
    actions.append(action)
    
    # Auto-execute if no approval needed
    auto_results = []
    if not action.need_approval:
        executor = ToolExecutor(session.root_path)
        try:
            result = await executor.execute(action.tool, action.args)
            action_result = ActionResult(
                action_id=action.id,
                success=True,
                result=result,
                error=None
            )
            
            # Log the action
            log_entry = LogEntry(
                action_id=action.id,
                tool=action.tool,
                args=action.args,
                success=True,
                result=result,
                error=None,
                session_id=session.id
            )
            await storage.save_log(log_entry)
            
            # Remove from pending actions
            await storage.delete_action(action.id)
            
            auto_results.append(action_result)
            
            # Send WebSocket notification
            if session.id in ws_connections:
                try:
                    await ws_connections[session.id].send_json({
                        "event": "tool_result",
                        "data": action_result.dict()
                    })
                except:
                    pass
        except Exception as e:
            action_result = ActionResult(
                action_id=action.id,
                success=False,
                result=None,
                error=str(e)
            )
            auto_results.append(action_result)
    
    return {
        "actions": actions,
        "auto_results": auto_results
    }

@app.post("/api/action/approve")
async def approve_action(request: ApprovalRequest):
    """Approve or deny an action"""
    # Get action
    action = await storage.get_action(request.action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    # Get session (if it exists)
    session = None
    if action.session_id:
        session = await storage.get_session(action.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    
    if request.decision == "deny":
        # Log denial
        if session:
            log_entry = LogEntry(
                action_id=action.id,
                tool=action.tool,
                args=action.args,
                success=False,
                result=None,
                error="User denied action",
                session_id=session.id
            )
            await storage.save_log(log_entry)
        await storage.delete_action(request.action_id)
        
        return {
            "action_id": request.action_id,
            "success": False,
            "result": None,
            "error": "User denied action"
        }
    
    # Execute the action
    root_path = session.root_path if session else settings.sandbox_path
    executor = ToolExecutor(root_path)
    
    try:
        result = await executor.execute(action.tool, action.args)
        
        # Log success
        if session:
            log_entry = LogEntry(
                action_id=action.id,
                tool=action.tool,
                args=action.args,
                success=True,
                result=result,
                error=None,
                session_id=session.id
            )
            await storage.save_log(log_entry)
        
        # Remove from pending actions
        await storage.delete_action(request.action_id)
        
        # Send WebSocket notification
        if session and session.id in ws_connections:
            try:
                await ws_connections[session.id].send_json({
                    "event": "tool_result",
                    "data": {
                        "action_id": action.id,
                        "success": True,
                        "result": result
                    }
                })
            except:
                pass
        
        return {
            "action_id": request.action_id,
            "success": True,
            "result": result,
            "error": None
        }
    
    except Exception as e:
        # Log failure
        if session:
            log_entry = LogEntry(
                action_id=action.id,
                tool=action.tool,
                args=action.args,
                success=False,
                result=None,
                error=str(e),
                session_id=session.id
            )
            await storage.save_log(log_entry)
        
        return {
            "action_id": request.action_id,
            "success": False,
            "result": None,
            "error": str(e)
        }

@app.get("/api/logs")
async def get_logs(session_id: str = Query(...)):
    """Get action logs for a session"""
    logs = await storage.get_logs(session_id)
    return {"logs": logs}

@app.get("/api/settings/root")
async def get_root_settings():
    """Get current root path settings"""
    root = await storage.get_setting("root_path", settings.sandbox_path)
    first_run = await storage.get_setting("first_run", True)
    
    return {
        "root": root,
        "first_run": first_run
    }

@app.post("/api/settings/root")
async def set_root_path(request: RootPathRequest):
    """Set root path"""
    # Use default if empty
    path = request.path.strip() if request.path else settings.sandbox_path
    
    # Save to storage
    await storage.save_setting("root_path", path)
    await storage.save_setting("first_run", False)
    
    return {"root": path}

@app.post("/api/settings/privilege_request")
async def request_privilege(request: PrivilegeRequest):
    """Request elevated privileges"""
    # Create a privilege request action
    action = Action(
        tool="privilege.request",
        args={
            "need": request.need,
            "target_path": request.target_path,
            "expires_minutes": request.expires_minutes,
            "reason_brief": request.reason_brief
        },
        need_approval=True,
        reason_brief=request.reason_brief,
        risk="high"
    )
    
    await storage.save_action(action)
    
    return {"action": action}

@app.websocket("/api/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    ws_connections[session_id] = websocket
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back or handle commands
            await websocket.send_json({"event": "pong", "data": {}})
    except WebSocketDisconnect:
        if session_id in ws_connections:
            del ws_connections[session_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
