"""
Utility functions and helpers for MULRAG application.

This module provides various utility functions and classes for logging,
timing, error handling, validation, caching, formatting, security,
rate limiting, system operations, and session naming.
"""

import time
import asyncio
import hashlib
import secrets
import psutil
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import logging

# Import all utility classes
from .session_namer import session_namer, SessionNamer
from pathlib import Path


# ==================== LOGGING UTILITIES ====================

class Logger:
    """Enhanced logging utility."""
    
    def __init__(self, name: str = "MULRAG"):
        """Initialize logger."""
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger configuration."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def info(self, message: str, **kwargs):
        """Log info message with optional context."""
        context_str = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"{message} | {context_str}" if context_str else message
        self.logger.info(full_message)
    
    def error(self, message: str, **kwargs):
        """Log error message with optional context."""
        context_str = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"{message} | {context_str}" if context_str else message
        self.logger.error(full_message)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional context."""
        context_str = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"{message} | {context_str}" if context_str else message
        self.logger.warning(full_message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional context."""
        context_str = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"{message} | {context_str}" if context_str else message
        self.logger.debug(full_message)


# Global logger instance
logger = Logger()


# ==================== TIMING UTILITIES ====================

class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, operation_name: str = "Operation", logger: Logger = None):
        """Initialize timer."""
        self.operation_name = operation_name
        self.logger = logger or Logger()
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        self.logger.info(f"[TIMER] {self.operation_name} started")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log result."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        self.logger.info(f"[TIMER] {self.operation_name} completed", duration=f"{duration:.2f}s")
        
        if exc_type:
            self.logger.error(f"[TIMER] {self.operation_name} failed", error=str(exc_val))
    
    @property
    def duration(self) -> float:
        """Get duration if timing is complete."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


def timing_decorator(operation_name: str = None):
    """Decorator for timing function execution."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with Timer(name):
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with Timer(name):
                return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# ==================== ERROR HANDLING UTILITIES ====================

class ErrorHandler:
    """Centralized error handling utility."""
    
    @staticmethod
    def handle_exception(e: Exception, context: str = "") -> Dict[str, Any]:
        """Handle and log exceptions."""
        error_info = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
            "traceback": traceback.format_exc()
        }
        
        logger.error(f"Exception in {context}", **error_info)
        return error_info
    
    @staticmethod
    def create_error_response(error_type: str, message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "success": False,
            "error": {
                "type": error_type,
                "message": message,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }


def safe_execute(func: Callable, *args, default_return: Any = None, **kwargs) -> Any:
    """Safely execute function with error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Safe execution failed for {func.__name__}", error=str(e))
        return default_return


# ==================== VALIDATION UTILITIES ====================

class Validator:
    """Input validation utilities."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password strength."""
        result = {
            "valid": True,
            "errors": []
        }
        
        if len(password) < 6:
            result["valid"] = False
            result["errors"].append("Password must be at least 6 characters long")
        
        if len(password) > 100:
            result["valid"] = False
            result["errors"].append("Password must be less than 100 characters long")
        
        # Check for at least one uppercase, lowercase, and digit
        if not any(c.isupper() for c in password):
            result["errors"].append("Password should contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            result["errors"].append("Password should contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            result["errors"].append("Password should contain at least one digit")
        
        return result
    
    @staticmethod
    def validate_file_upload(filename: str, file_size: int, allowed_extensions: set, max_size: int) -> Dict[str, Any]:
        """Validate file upload."""
        result = {
            "valid": True,
            "errors": []
        }
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_extensions:
            result["valid"] = False
            result["errors"].append(f"File type {file_ext} not allowed. Allowed types: {allowed_extensions}")
        
        # Check file size
        if file_size > max_size:
            result["valid"] = False
            result["errors"].append(f"File size {file_size} exceeds maximum allowed size {max_size}")
        
        return result
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = None) -> str:
        """Sanitize string input."""
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        import re
        sanitized = re.sub(r'[<>"\']', '', text)
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        # Limit length
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized


# ==================== CACHE UTILITIES ====================

class SimpleCache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self, default_ttl: int = 3600):
        """Initialize cache."""
        self.cache = {}
        self.default_ttl = default_ttl
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Set cache value with TTL."""
        expire_time = datetime.utcnow() + timedelta(seconds=ttl or self.default_ttl)
        self.cache[key] = {
            "value": value,
            "expire_time": expire_time
        }
    
    def get(self, key: str) -> Any:
        """Get cache value if not expired."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if datetime.utcnow() > entry["expire_time"]:
            del self.cache[key]
            return None
        
        return entry["value"]
    
    def delete(self, key: str):
        """Delete cache entry."""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
    
    def cleanup_expired(self):
        """Remove expired entries."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now > entry["expire_time"]
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def size(self) -> int:
        """Get cache size."""
        return len(self.cache)


# ==================== FORMATTING UTILITIES ====================

class Formatter:
    """Text and data formatting utilities."""
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.2f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to specified length."""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def format_timestamp(timestamp: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format timestamp to string."""
        return timestamp.strftime(format_str)
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction based on word frequency
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in keywords[:max_keywords]]


# ==================== SECURITY UTILITIES ====================

class SecurityUtils:
    """Security-related utilities."""
    
    @staticmethod
    def generate_random_string(length: int = 32) -> str:
        """Generate cryptographically secure random string."""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
        """Mask sensitive data for logging."""
        if len(data) <= visible_chars:
            return mask_char * len(data)
        
        return data[:visible_chars] + mask_char * (len(data) - visible_chars)
    
    @staticmethod
    def is_safe_path(path: str, base_path: str) -> bool:
        """Check if path is safe (doesn't escape base directory)."""
        try:
            base = Path(base_path).resolve()
            target = Path(path).resolve()
            return base in target.parents or base == target
        except Exception:
            return False


# ==================== RATE LIMITING UTILITIES ====================

class RateLimiter:
    """Simple rate limiter."""
    
    def __init__(self, max_requests: int, time_window: int):
        """Initialize rate limiter."""
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        
        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < self.time_window
            ]
        else:
            self.requests[identifier] = []
        
        # Check if under limit
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True
        
        return False
    
    def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests for identifier."""
        now = time.time()
        
        if identifier not in self.requests:
            return self.max_requests
        
        # Count recent requests
        recent_requests = sum(
            1 for req_time in self.requests[identifier]
            if now - req_time < self.time_window
        )
        
        return max(0, self.max_requests - recent_requests)


# ==================== SYSTEM UTILITIES ====================

class SystemUtils:
    """System-related utilities."""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get system information."""
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "used": psutil.disk_usage('/').used
            }
        }
    
    @staticmethod
    def ensure_directory(path: str) -> bool:
        """Ensure directory exists."""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}", error=str(e))
            return False
    
    @staticmethod
    def cleanup_old_files(directory: str, max_age_days: int = 7) -> int:
        """Clean up old files in directory."""
        try:
            directory_path = Path(directory)
            if not directory_path.exists():
                return 0
            
            cutoff_time = time.time() - (max_age_days * 24 * 3600)
            deleted_count = 0
            
            for file_path in directory_path.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old files from {directory}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old files in {directory}", error=str(e))
            return 0


# ==================== EXPORTS ====================

__all__ = [
    "Logger", "logger",
    "Timer", "timing_decorator",
    "ErrorHandler", "safe_execute",
    "Validator",
    "SimpleCache",
    "Formatter",
    "SecurityUtils",
    "RateLimiter",
    "SystemUtils"
]
