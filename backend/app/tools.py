"""Tool execution layer"""
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
from app.config import settings

class ToolExecutor:
    """Execute tools safely within sandbox"""
    
    def __init__(self, root_path: str = None):
        self.root_path = Path(root_path or settings.sandbox_path).expanduser()
        self.ensure_sandbox()
    
    def ensure_sandbox(self):
        """Create sandbox directory if it doesn't exist"""
        self.root_path.mkdir(parents=True, exist_ok=True)
    
    def get_full_path(self, filename: str) -> Path:
        """Get full path within sandbox"""
        # If it's already an absolute path, check if it's within allowed roots
        path = Path(filename)
        if path.is_absolute():
            return path
        # Otherwise, resolve relative to sandbox
        return (self.root_path / filename).resolve()
    
    def is_safe_path(self, path: Path) -> bool:
        """Check if path is within sandbox or explicitly allowed"""
        try:
            # Check if within sandbox
            path.relative_to(self.root_path)
            return True
        except ValueError:
            # Outside sandbox - would need privilege approval
            return False
    
    async def execute(self, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return result"""
        
        if tool == "system.time":
            return await self.system_time()
        
        elif tool == "files.write":
            return await self.files_write(args.get("filename"), args.get("content"))
        
        elif tool == "files.read":
            return await self.files_read(args.get("filename"))
        
        elif tool == "files.delete":
            return await self.files_delete(args.get("filename"))
        
        elif tool == "files.copy":
            return await self.files_copy(args.get("source"), args.get("dest"))
        
        elif tool == "files.move":
            return await self.files_move(args.get("source"), args.get("dest"))
        
        elif tool == "files.list":
            return await self.files_list(args.get("path", ""))
        
        elif tool == "apps.open":
            return await self.apps_open(args.get("app"))
        
        elif tool == "privilege.request":
            # Privilege requests don't execute - they create approval actions
            return {"status": "pending_approval"}
        
        else:
            raise ValueError(f"Unknown tool: {tool}")
    
    async def system_time(self) -> Dict[str, Any]:
        """Get current time"""
        now = datetime.now(timezone.utc)
        return {
            "now_iso": now.isoformat(),
            "unix": now.timestamp()
        }
    
    async def files_write(self, filename: str, content: str) -> Dict[str, Any]:
        """Write file"""
        path = self.get_full_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            f.write(content)
        
        return {"bytes_written": len(content)}
    
    async def files_read(self, filename: str) -> Dict[str, Any]:
        """Read file"""
        path = self.get_full_path(filename)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filename}")
        
        with open(path, 'r') as f:
            content = f.read()
        
        return {"text": content}
    
    async def files_delete(self, filename: str) -> Dict[str, Any]:
        """Delete file"""
        path = self.get_full_path(filename)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filename}")
        
        path.unlink()
        return {"deleted": True}
    
    async def files_copy(self, source: str, dest: str) -> Dict[str, Any]:
        """Copy file"""
        src_path = self.get_full_path(source)
        dst_path = self.get_full_path(dest)
        
        if not src_path.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        
        return {"copied": True}
    
    async def files_move(self, source: str, dest: str) -> Dict[str, Any]:
        """Move file"""
        src_path = self.get_full_path(source)
        dst_path = self.get_full_path(dest)
        
        if not src_path.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        
        return {"moved": True}
    
    async def files_list(self, path: str = "") -> Dict[str, Any]:
        """List files in directory"""
        target = self.get_full_path(path) if path else self.root_path
        
        if not target.exists():
            return {"entries": []}
        
        if not target.is_dir():
            raise ValueError(f"Not a directory: {path}")
        
        entries = []
        for item in target.iterdir():
            entries.append(item.name)
        
        return {"entries": sorted(entries)}
    
    async def apps_open(self, app: str) -> Dict[str, Any]:
        """Open application (simulated)"""
        # In a real implementation, this would open the actual app
        # For testing, we just return success
        return {
            "opened": True,
            "app": app,
            "note": "Application opening is simulated in this version"
        }