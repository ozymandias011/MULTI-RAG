"""
Database operations and connection management for MULRAG application.

This module handles MongoDB connections, CRUD operations, and data access
for users, sessions, messages, and logs.
"""

import os
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from pymongo import MongoClient
from pymongo.errors import PyMongoError as DatabaseError
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..config import settings
from ..models import (
    UserDocument, SessionDocument, MessageDocument, LogDocument,
    UserResponse, SessionResponse, MessageResponse
)


class DatabaseManager:
    """Main database manager class."""
    
    def __init__(self):
        """Initialize database connection."""
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection."""
        try:
            self.client = MongoClient(settings.MONGO_URI)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[settings.DB_NAME]
            print(f"[DB] Connected to MongoDB: {settings.DB_NAME}")
        except Exception as e:
            print(f"[DB] Connection failed: {str(e)}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            print("[DB] Connection closed")
    
    @property
    def users(self):
        """Get users collection."""
        return self.db[settings.USERS_COLLECTION]
    
    @property
    def sessions(self):
        """Get sessions collection."""
        return self.db[settings.SESSIONS_COLLECTION]
    
    @property
    def messages(self):
        """Get messages collection."""
        return self.db[settings.MESSAGES_COLLECTION]
    
    @property
    def logs(self):
        """Get logs collection."""
        return self.db[settings.LOGS_COLLECTION]


class UserRepository:
    """Repository for user operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize user repository."""
        self.collection = db_manager.users
    
    async def create_user(self, user_data: UserDocument) -> str:
        """Create a new user."""
        try:
            start_time = time.time()
            result = self.collection.insert_one(user_data.dict())
            user_id = str(result.inserted_id)
            print(f"[DB] User created in {time.time() - start_time:.2f}s")
            return user_id
        except PyMongoError as e:
            print(f"[DB] Error creating user: {str(e)}")
            raise
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            return self.collection.find_one({"email": email})
        except PyMongoError as e:
            print(f"[DB] Error getting user by email: {str(e)}")
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            return self.collection.find_one({"_id": ObjectId(user_id)})
        except PyMongoError as e:
            print(f"[DB] Error getting user by ID: {str(e)}")
            raise
    
    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except PyMongoError as e:
            print(f"[DB] Error updating last login: {str(e)}")
            raise
    
    async def user_exists(self, email: str = None, username: str = None) -> bool:
        """Check if user exists by email or username."""
        try:
            query = {}
            if email:
                query["email"] = email
            if username:
                query["username"] = username
            
            return self.collection.count_documents(query) > 0
        except PyMongoError as e:
            print(f"[DB] Error checking user existence: {str(e)}")
            raise


class SessionRepository:
    """Repository for chat session operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize session repository."""
        self.collection = db_manager.sessions
    
    async def create_session(self, session_data: SessionDocument) -> str:
        """Create a new chat session."""
        try:
            start_time = time.time()
            result = self.collection.insert_one(session_data.dict())
            session_id = str(result.inserted_id)
            print(f"[DB] Session created in {time.time() - start_time:.2f}s")
            return session_id
        except PyMongoError as e:
            print(f"[DB] Error creating session: {str(e)}")
            raise
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        try:
            start_time = time.time()
            sessions = list(self.collection.find(
                {"user_id": user_id}
            ).sort("updated_at", -1))
            print(f"[DB] Fetched {len(sessions)} sessions in {time.time() - start_time:.2f}s")
            return sessions
        except PyMongoError as e:
            print(f"[DB] Error getting user sessions: {str(e)}")
            raise
    
    async def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        try:
            return self.collection.find_one({"_id": ObjectId(session_id)})
        except PyMongoError as e:
            print(f"[DB] Error getting session by ID: {str(e)}")
            raise
    
    async def get_user_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID and verify user ownership."""
        try:
            return self.collection.find_one({
                "_id": ObjectId(session_id),
                "user_id": user_id
            })
        except PyMongoError as e:
            print(f"[DB] Error getting user session: {str(e)}")
            raise
    
    async def update_session(self, session_id: str, **kwargs) -> bool:
        """Update session fields."""
        try:
            update_data = {
                "$set": {**kwargs, "updated_at": datetime.utcnow()}
            }
            result = self.collection.update_one(
                {"_id": ObjectId(session_id)},
                update_data
            )
            return result.modified_count > 0
        except PyMongoError as e:
            print(f"[DB] Error updating session: {str(e)}")
            raise
    
    async def increment_message_count(self, session_id: str, count: int = 1) -> bool:
        """Increment session message count."""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$set": {"updated_at": datetime.utcnow()},
                    "$inc": {"message_count": count}
                }
            )
            return result.modified_count > 0
        except PyMongoError as e:
            print(f"[DB] Error incrementing message count: {str(e)}")
            raise
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session."""
        try:
            start_time = time.time()
            result = self.collection.delete_one({
                "_id": ObjectId(session_id),
                "user_id": user_id
            })
            deleted = result.deleted_count > 0
            print(f"[DB] Session deleted in {time.time() - start_time:.2f}s")
            return deleted
        except PyMongoError as e:
            print(f"[DB] Error deleting session: {str(e)}")
            raise


class MessageRepository:
    """Repository for chat message operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize message repository."""
        self.collection = db_manager.messages
    
    async def create_message(self, message_data: MessageDocument) -> str:
        """Create a new message."""
        try:
            result = self.collection.insert_one(message_data.dict())
            return str(result.inserted_id)
        except PyMongoError as e:
            print(f"[DB] Error creating message: {str(e)}")
            raise
    
    async def get_session_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session."""
        try:
            start_time = time.time()
            count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.collection.count_documents({"session_id": session_id})
            )
            print(f"[DB] Retrieved message count for session {session_id}: {count}")
            return count
        except PyMongoError as e:
            print(f"[DB] Error getting message count: {str(e)}")
            raise
    
    async def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a session."""
        try:
            start_time = time.time()
            messages = list(self.collection.find(
                {"session_id": session_id}
            ).sort("created_at", 1))
            print(f"[DB] Fetched {len(messages)} messages in {time.time() - start_time:.2f}s")
            return messages
        except PyMongoError as e:
            print(f"[DB] Error getting session messages: {str(e)}")
            raise
    
    async def get_recent_messages(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent messages for a session."""
        try:
            return list(self.collection.find(
                {"session_id": session_id}
            ).sort("created_at", -1).limit(limit))
        except PyMongoError as e:
            print(f"[DB] Error getting recent messages: {str(e)}")
            raise
    
    async def delete_session_messages(self, session_id: str) -> int:
        """Delete all messages for a session."""
        try:
            result = self.collection.delete_many({"session_id": session_id})
            return result.deleted_count
        except PyMongoError as e:
            print(f"[DB] Error deleting session messages: {str(e)}")
            raise


class LogRepository:
    """Repository for logging operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize log repository."""
        self.collection = db_manager.logs
    
    async def create_log(self, log_data: LogDocument) -> str:
        """Create a new log entry."""
        try:
            result = self.collection.insert_one(log_data.dict())
            return str(result.inserted_id)
        except PyMongoError as e:
            print(f"[DB] Error creating log: {str(e)}")
            raise
    
    async def create_log_from_request(self, timestamp: str, auth_header: str, request_data: Dict[str, Any]) -> str:
        """Create log entry from request data."""
        log_data = LogDocument(
            timestamp=timestamp,
            auth_header=auth_header,
            request_data=request_data
        )
        return await self.create_log(log_data)


# Database instance and repositories
db_manager = DatabaseManager()
user_repo = UserRepository(db_manager)
session_repo = SessionRepository(db_manager)
message_repo = MessageRepository(db_manager)
log_repo = LogRepository(db_manager)


# Helper functions for data conversion
def convert_user_to_response(user_doc: Dict[str, Any]) -> UserResponse:
    """Convert user document to response model."""
    return UserResponse(
        id=str(user_doc["_id"]),
        username=user_doc["username"],
        email=user_doc["email"],
        created_at=user_doc["created_at"],
        last_login=user_doc.get("last_login")
    )


def convert_session_to_response(session_doc: Dict[str, Any]) -> SessionResponse:
    """Convert session document to response model."""
    return SessionResponse(
        id=str(session_doc["_id"]),
        title=session_doc["title"],
        message_count=session_doc.get("message_count", 0),
        created_at=session_doc["created_at"],
        updated_at=session_doc["updated_at"],
        document_id=session_doc.get("document_id"),
        document_url=session_doc.get("document_url")
    )


def convert_message_to_response(message_doc: Dict[str, Any]) -> MessageResponse:
    """Convert message document to response model."""
    return MessageResponse(
        id=str(message_doc["_id"]),
        type=message_doc["type"],
        content=message_doc["content"],
        processing_time=message_doc.get("processing_time"),
        created_at=message_doc["created_at"],
        metadata=message_doc.get("metadata")
    )
