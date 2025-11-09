"""Configuration management"""
import os
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    
    # Database
    storage_mode: Literal["memory", "sqlite"] = "sqlite"
    db_path: str = "./axion.db"
    mongo_url: str = ""  # For compatibility with existing .env
    
    # Parser
    parser_mode: Literal["rules", "hybrid", "llm"] = "rules"
    confidence_low: float = 0.55
    confidence_high: float = 0.80
    
    # LLM (optional)
    llm_api_key: str = ""
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    
    # Security
    sandbox_path: str = "~/Desktop/Axion"
    max_session_minutes: int = 60
    
    # CORS
    cors_origins: str = "*"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Allow extra fields for compatibility

settings = Settings()

# Expand sandbox path
settings.sandbox_path = str(Path(settings.sandbox_path).expanduser())