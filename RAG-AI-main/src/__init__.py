"""
MULRAG - Multi-Agent RAG System

A sophisticated document analysis and question answering system using
multiple AI agents for enhanced retrieval and generation capabilities.

This package contains the core modules for the MULRAG system:
- config: Configuration management
- models: Data models and schemas
- database: Database operations and repositories
- auth: Authentication and authorization
- agents: Multi-agent RAG system
- document_processing: Document processing pipeline
- api: API routes and endpoints
- utils: Utility functions and helpers
"""

__version__ = "1.0.0"
__author__ = "MULRAG Team"
__description__ = "Multi-Agent RAG System for Document Analysis"

# Import key components for easier access
from .config import settings
from .models import *
from .database import *
from .auth import *
from .agents import *
from .document_processing import *
from .api import *
from .utils import *

__all__ = [
    "settings",
    # Models
    "UserRegister", "UserLogin", "CreateSession", "QueryRequest",
    "AuthResponse", "SessionResponse", "MessageResponse", "ChatResponse",
    # Database
    "DatabaseManager", "UserRepository", "SessionRepository", "MessageRepository",
    # Auth
    "AuthenticationService", "TokenManager", "PasswordManager",
    # Agents
    "MultiAgentRAGSystem", "QuestionUnderstandingAgent", "HistoryAnalysisAgent",
    "ContextRetrievalAgent", "AnswerGenerationAgent",
    # Document Processing
    "DocumentProcessor", "EmbeddingManager", "SearchManager",
    # API
    "include_routers",
    # Utils
    "Logger", "Timer", "Validator", "Formatter", "ErrorHandler"
]
