"""
Data models and schemas for MULRAG application.

This module contains Pydantic models, database schemas, and data structures
used throughout the application for request/response validation and data storage.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId


# Pydantic Models for API Requests/Responses
class UserRegister(BaseModel):
    """User registration request model."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """User login request model."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model."""
    id: str
    username: str
    email: str
    created_at: datetime
    last_login: Optional[datetime] = None


class CreateSession(BaseModel):
    """Create chat session request model."""
    title: str = Field(..., min_length=1, max_length=100)
    document_id: Optional[str] = None
    document_url: Optional[str] = None


class SessionResponse(BaseModel):
    """Chat session response model."""
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    document_id: Optional[str] = None
    document_url: Optional[str] = None


class MessageResponse(BaseModel):
    """Chat message response model."""
    id: str
    type: str  # 'user' or 'bot'
    content: str
    processing_time: Optional[str] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class ChatHistoryResponse(BaseModel):
    """Chat history response model."""
    session: SessionResponse
    messages: List[MessageResponse]


class QueryRequest(BaseModel):
    """Original backward compatibility query request."""
    documents: str
    questions: List[str]


class ChatRequest(BaseModel):
    """Chat request model."""
    question: str
    session_id: str


class ChatResponse(BaseModel):
    """Chat response model."""
    success: bool
    answer: str
    processing_time: str
    question: str
    metadata: Dict[str, Any]


class UploadResponse(BaseModel):
    """File upload response model."""
    success: bool
    file_id: str
    filename: str
    message: str


class AuthResponse(BaseModel):
    """Authentication response model."""
    success: bool
    token: str
    user: UserResponse


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Database Models (MongoDB)
class UserDocument(BaseModel):
    """User document model for MongoDB."""
    username: str
    email: str
    password: str  # Hashed password
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None


class SessionDocument(BaseModel):
    """Chat session document model for MongoDB."""
    user_id: str
    title: str
    document_id: Optional[str] = None
    document_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0


class MessageDocument(BaseModel):
    """Chat message document model for MongoDB."""
    session_id: str
    type: str  # 'user' or 'bot'
    content: str
    processing_time: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class LogDocument(BaseModel):
    """Log document model for MongoDB."""
    timestamp: str
    auth_header: Optional[str] = None
    request_data: Dict[str, Any]


# Internal Data Structures
class DocumentCache(BaseModel):
    """Document cache entry model."""
    chunks: List[str]
    faiss_index: Any  # FAISS index object
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)


class AgentResult(BaseModel):
    """Agent processing result model."""
    agent_name: str
    processing_time: float
    result: Any
    metadata: Optional[Dict[str, Any]] = None


class QuestionUnderstanding(BaseModel):
    """Question understanding result."""
    understood_question: str
    intent: str


class RetrievalResult(BaseModel):
    """Document retrieval result."""
    chunks: List[str]
    scores: List[float]
    query_embedding: Any


class ChatContext(BaseModel):
    """Chat context for RAG processing."""
    original_question: str
    understood_question: str
    intent: str
    document_context: List[str]
    chat_history: List[Dict[str, Any]]


# Helper class for ObjectId conversion
class PyObjectId(ObjectId):
    """Custom ObjectId class for Pydantic validation."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
        return field_schema


# Configuration for model serialization
class Config:
    """Pydantic configuration."""
    json_encoders = {
        ObjectId: str,
        datetime: lambda v: v.isoformat()
    }
    populate_by_name = True
    arbitrary_types_allowed = True


# Models with ObjectId support
class UserDocumentWithId(UserDocument):
    """User document with ObjectId."""
    
    model_config = {
        "json_encoders": {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        },
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")


class SessionDocumentWithId(SessionDocument):
    """Session document with ObjectId."""
    
    model_config = {
        "json_encoders": {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        },
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")


class MessageDocumentWithId(MessageDocument):
    """Message document with ObjectId."""
    
    model_config = {
        "json_encoders": {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        },
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
