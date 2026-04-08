"""
Main application entry point for MULRAG - Multi-Agent RAG System.

This file initializes the FastAPI application, configures all modules,
and sets up the server. It serves as the central orchestrator for the
entire application.
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import application modules
from src.config import settings
from src.database import db_manager
from src.auth import auth_service
from src.document_processing import initialize_document_processing
from src.api import include_routers
from src.utils import logger, SystemUtils


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting MULRAG application...")
    
    try:
        # Initialize Azure OpenAI client
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            api_version=settings.OPENAI_API_VERSION,
            azure_endpoint=settings.OPENAI_API_BASE,
            api_key=settings.OPENAI_API_KEY,
            max_retries=5
        )
        
        # Set client in auth service
        auth_service.client = client
        
        # Initialize document processing
        initialize_document_processing(client)
        
        # Ensure required directories exist
        SystemUtils.ensure_directory(settings.UPLOAD_DIR)
        SystemUtils.ensure_directory(settings.TEMP_UPLOAD_DIR)
        
        # Test database connection
        db_info = db_manager.db.command("ping")
        logger.info("Database connection successful")
        
        # Log system info
        system_info = SystemUtils.get_system_info()
        logger.info("System information", **system_info)
        
        logger.info("MULRAG application started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down MULRAG application...")
        
        # Close database connection
        db_manager.close()
        
        logger.info("MULRAG application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    # Initialize FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="Multi-Agent RAG System for intelligent document analysis and question answering",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    if os.path.exists("app/static"):
        app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # Include API routers
    include_routers(app)
    
    # Root endpoint - serve the main HTML page
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the main application page."""
        from fastapi.templating import Jinja2Templates
        
        templates = Jinja2Templates(directory="app/templates")
        return templates.TemplateResponse("index.html", {"request": {}})
    
    # API info endpoint
    @app.get("/api")
    async def api_info():
        """API information endpoint."""
        return {
            "message": "Welcome to MULRAG - Multi-Agent RAG System",
            "version": settings.VERSION,
            "status": "running",
            "endpoints": {
                "health": "/api/v1/auth/health",
                "docs": "/docs",
                "auth": "/api/v1/auth/",
                "sessions": "/api/v1/sessions/",
                "chat": "/api/v1/chat",
                "upload": "/api/v1/upload-pdf"
            }
        }
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
