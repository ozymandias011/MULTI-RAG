"""
Authentication module for MULRAG application.

This module handles user authentication, JWT token management, password hashing,
and authentication middleware for API endpoints.
"""

import time
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import settings
from ..database import user_repo
from ..models import UserRegister, UserLogin, AuthResponse, UserResponse


class AuthenticationError(Exception):
    """Custom authentication error."""
    pass


class TokenManager:
    """JWT token management class."""
    
    @staticmethod
    def create_token(user_id: str, email: str) -> str:
        """Create JWT token for user."""
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
        except Exception as e:
            raise AuthenticationError(f"Token verification failed: {str(e)}")


class PasswordManager:
    """Password hashing and verification class."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False


class AuthenticationService:
    """Main authentication service class."""
    
    def __init__(self):
        """Initialize authentication service."""
        self.token_manager = TokenManager()
        self.password_manager = PasswordManager()
        self.security = HTTPBearer()
    
    async def register_user(self, user_data: UserRegister) -> AuthResponse:
        """Register a new user."""
        start_time = time.time()
        print(f"[AUTH] Registration attempt for: {user_data.email}")
        
        try:
            # Check if user already exists
            if await user_repo.user_exists(email=user_data.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            if await user_repo.user_exists(username=user_data.username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            
            # Hash password
            hashed_password = self.password_manager.hash_password(user_data.password)
            
            # Create user document
            from ..models import UserDocument
            user_doc = UserDocument(
                username=user_data.username,
                email=user_data.email,
                password=hashed_password,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            
            # Save user to database
            user_id = await user_repo.create_user(user_doc)
            
            # Create JWT token
            token = self.token_manager.create_token(user_id, user_data.email)
            
            # Create response
            user_response = UserResponse(
                id=user_id,
                username=user_data.username,
                email=user_data.email,
                created_at=user_doc.created_at,
                last_login=user_doc.last_login
            )
            
            print(f"[AUTH] User registered successfully in {time.time() - start_time:.2f}s")
            
            return AuthResponse(
                success=True,
                token=token,
                user=user_response
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"[AUTH] Registration error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: {str(e)}"
            )
    
    async def login_user(self, credentials: UserLogin) -> AuthResponse:
        """Login user."""
        start_time = time.time()
        print(f"[AUTH] Login attempt for: {credentials.email}")
        
        try:
            # Find user by email
            user_doc = await user_repo.get_user_by_email(credentials.email)
            if not user_doc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Verify password
            if not self.password_manager.verify_password(credentials.password, user_doc["password"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Update last login
            await user_repo.update_last_login(str(user_doc["_id"]))
            
            # Create JWT token
            token = self.token_manager.create_token(str(user_doc["_id"]), user_doc["email"])
            
            # Create response
            user_response = UserResponse(
                id=str(user_doc["_id"]),
                username=user_doc["username"],
                email=user_doc["email"],
                created_at=user_doc["created_at"],
                last_login=datetime.utcnow()
            )
            
            print(f"[AUTH] Login successful in {time.time() - start_time:.2f}s")
            
            return AuthResponse(
                success=True,
                token=token,
                user=user_response
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"[AUTH] Login error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Login failed: {str(e)}"
            )
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Dict[str, Any]:
        """Get current user from JWT token."""
        try:
            token = credentials.credentials
            payload = self.token_manager.verify_token(token)
            
            # Get user from database
            user_doc = await user_repo.get_user_by_id(payload["user_id"])
            if not user_doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return user_doc
            
        except AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"[AUTH] Get current user error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    async def get_current_user_response(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> UserResponse:
        """Get current user as response model."""
        user_doc = await self.get_current_user(credentials)
        return UserResponse(
            id=str(user_doc["_id"]),
            username=user_doc["username"],
            email=user_doc["email"],
            created_at=user_doc["created_at"],
            last_login=user_doc.get("last_login")
        )


# Global authentication service instance
auth_service = AuthenticationService()


# Dependency functions for FastAPI
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Dict[str, Any]:
    """Dependency to get current authenticated user."""
    return await auth_service.get_current_user(credentials)


async def get_current_user_response(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> UserResponse:
    """Dependency to get current user as response model."""
    return await auth_service.get_current_user_response(credentials)


# Authentication middleware class
class AuthMiddleware:
    """Authentication middleware for protecting routes."""
    
    def __init__(self, auth_service: AuthenticationService):
        """Initialize auth middleware."""
        self.auth_service = auth_service
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        return self.auth_service.token_manager.verify_token(token)
    
    async def authenticate_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with token."""
        try:
            payload = await self.verify_token(token)
            user_doc = await user_repo.get_user_by_id(payload["user_id"])
            return user_doc
        except Exception:
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired."""
        try:
            payload = self.auth_service.token_manager.verify_token(token)
            return False
        except AuthenticationError as e:
            return "expired" in str(e).lower()
        except Exception:
            return True


# Helper functions
def create_user_response(user_doc: Dict[str, Any]) -> UserResponse:
    """Convert user document to response model."""
    return UserResponse(
        id=str(user_doc["_id"]),
        username=user_doc["username"],
        email=user_doc["email"],
        created_at=user_doc["created_at"],
        last_login=user_doc.get("last_login")
    )


def extract_token_from_header(authorization: str) -> Optional[str]:
    """Extract JWT token from authorization header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization.replace("Bearer ", "")
    return None


# Rate limiting for authentication endpoints
class AuthRateLimiter:
    """Simple rate limiter for auth endpoints."""
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        """Initialize rate limiter."""
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self.attempts = {}  # {ip: [(timestamp, success), ...]}
    
    def is_rate_limited(self, ip: str) -> bool:
        """Check if IP is rate limited."""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=self.window_minutes)
        
        # Clean old attempts
        if ip in self.attempts:
            self.attempts[ip] = [
                (timestamp, success) for timestamp, success in self.attempts[ip]
                if timestamp > cutoff
            ]
        
        # Check recent failed attempts
        recent_failures = sum(
            1 for timestamp, success in self.attempts.get(ip, [])
            if not success and timestamp > cutoff
        )
        
        return recent_failures >= self.max_attempts
    
    def record_attempt(self, ip: str, success: bool):
        """Record authentication attempt."""
        if ip not in self.attempts:
            self.attempts[ip] = []
        
        self.attempts[ip].append((datetime.utcnow(), success))
        
        # Keep only recent attempts
        cutoff = datetime.utcnow() - timedelta(minutes=self.window_minutes)
        self.attempts[ip] = [
            (timestamp, success) for timestamp, success in self.attempts[ip]
            if timestamp > cutoff
        ]


# Global rate limiter instance
auth_rate_limiter = AuthRateLimiter()
