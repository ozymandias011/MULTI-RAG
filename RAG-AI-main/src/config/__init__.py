"""
Configuration module for MULRAG application.

This module handles all environment variables and application settings.
It provides centralized configuration management for the entire application.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings and configuration."""
    
    # Application Settings
    APP_NAME: str = "MULRAG - Multi-Agent RAG System"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # JWT Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "168"))  # 7 days
    
    # Azure OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE")
    OPENAI_API_VERSION: str = os.getenv("OPENAI_API_VERSION", "2024-12-01-preview")
    OPENAI_DEPLOYMENT: str = os.getenv("OPENAI_DEPLOYMENT", "gpt-4o-mini")
    OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv("OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
    
    # MongoDB Configuration
    MONGO_URI: str = os.getenv("MONGO_URI")
    DB_NAME: str = os.getenv("DB_NAME", "hackrx_logs")
    
    # Collections
    USERS_COLLECTION: str = "users"
    SESSIONS_COLLECTION: str = "chat_sessions"
    MESSAGES_COLLECTION: str = "chat_messages"
    LOGS_COLLECTION: str = "CheckRequest"
    
    # File Upload Settings
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 100MB
    ALLOWED_EXTENSIONS: set = {'.pdf'}
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "app/uploads")
    TEMP_UPLOAD_DIR: str = os.getenv("TEMP_UPLOAD_DIR", "temp_uploads")
    
    # RAG Configuration
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    MIN_CHUNK_WORDS: int = int(os.getenv("MIN_CHUNK_WORDS", "5"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "20"))
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "75"))
    
    # Chat Configuration
    MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
    MAX_HISTORY_EXCHANGES: int = int(os.getenv("MAX_HISTORY_EXCHANGES", "5"))
    
    # Pinecone Configuration (if used)
    PINECONE_API_KEY: Optional[str] = os.getenv("pinecone_api_key")
    PINECONE_ENV: Optional[str] = os.getenv("PINECONE_ENV")
    PINECONE_INDEX: Optional[str] = os.getenv("PINECONE_INDEX")
    
    def __init__(self):
        """Validate configuration on initialization."""
        self._validate_config()
    
    def _validate_config(self):
        """Validate required configuration variables."""
        required_vars = [
            "OPENAI_API_KEY",
            "OPENAI_API_BASE", 
            "MONGO_URI"
        ]
        
        missing_vars = [var for var in required_vars if not getattr(self, var)]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return not self.DEBUG and self.JWT_SECRET != "your-secret-key-change-in-production"


# Global settings instance
settings = Settings()
