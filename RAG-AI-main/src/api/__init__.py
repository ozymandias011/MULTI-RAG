"""
API routes module for MULRAG application.

This module contains all API endpoints organized by functionality:
- Authentication routes (register, login, user info)
- Session management routes (create, list, get, delete sessions)
- Document upload routes
- Chat and RAG routes
- Legacy compatibility routes
"""

import time
import os
import asyncio
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Header, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from src.flashcards.service import router as flashcards_router

from ..config import settings
from ..models import (
    UserRegister, UserLogin, CreateSession, QueryRequest,
    AuthResponse, SessionResponse, ChatHistoryResponse, UploadResponse
)
from ..auth import auth_service, get_current_user
from ..database import (
    user_repo, session_repo, message_repo, log_repo,
    convert_user_to_response, convert_session_to_response, convert_message_to_response
)
from ..agents import MultiAgentRAGSystem
from ..document_processing import document_processor


# Create routers for different API sections
auth_router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
session_router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
upload_router = APIRouter(prefix="/api/v1", tags=["uploads"])
chat_router = APIRouter(prefix="/api/v1", tags=["chat"])
legacy_router = APIRouter(prefix="/api/v1", tags=["legacy"])


# ==================== AUTHENTICATION ROUTES ====================

@auth_router.post("/register", response_model=AuthResponse)
async def register(user_data: UserRegister):
    """Register a new user."""
    return await auth_service.register_user(user_data)


@auth_router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin):
    """Login user and return JWT token."""
    return await auth_service.login_user(credentials)


@auth_router.get("/me")
async def get_me(current_user = Depends(get_current_user)):
    """Get current user information."""
    user_response = convert_user_to_response(current_user)
    return {
        "success": True,
        "user": user_response.dict()
    }


# ==================== SESSION MANAGEMENT ROUTES ====================

@session_router.post("/create", response_model=Dict[str, Any])
async def create_session(session_data: CreateSession, current_user = Depends(get_current_user)):
    """Create a new chat session."""
    start_time = time.time()
    print(f"\n[SESSION] Creating new session for user: {current_user['username']}")
    
    try:
        # Create session document
        from ..models import SessionDocument
        session_doc = SessionDocument(
            user_id=str(current_user["_id"]),
            title=session_data.title,
            document_id=session_data.document_id,
            document_url=session_data.document_url,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            message_count=0
        )
        
        # Save to database
        session_id = await session_repo.create_session(session_doc)
        
        # Create response
        session_response = convert_session_to_response({
            "_id": session_id,
            **session_doc.dict()
        })
        
        print(f"[SESSION] Session created: {session_id}")
        print(f"[SESSION] Document ID: {session_data.document_id}")
        print(f"[SESSION] Document URL: {session_data.document_url}")
        print(f"[SESSION] Created in {time.time() - start_time:.2f}s")
        
        return {
            "success": True,
            "session_id": session_id,
            "session": session_response.dict()
        }
        
    except Exception as e:
        print(f"[SESSION] Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@session_router.get("/list")
async def list_sessions(current_user = Depends(get_current_user)):
    """Get all sessions for the current user."""
    start_time = time.time()
    print(f"\n[SESSION] Fetching sessions for user: {current_user['username']}")
    
    try:
        # Get user sessions
        sessions = await session_repo.get_user_sessions(str(current_user["_id"]))
        
        # Convert to response models
        session_list = []
        for session in sessions:
            session_response = convert_session_to_response(session)
            session_list.append(session_response.dict())
        
        print(f"[SESSION] Fetched {len(session_list)} sessions in {time.time() - start_time:.2f}s")
        
        return {
            "success": True,
            "sessions": session_list
        }
        
    except Exception as e:
        print(f"[SESSION] Error fetching sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")


@session_router.get("/{session_id}/messages", response_model=ChatHistoryResponse)
async def get_session_messages(session_id: str, current_user = Depends(get_current_user)):
    """Get all messages in a session."""
    start_time = time.time()
    print(f"\n[SESSION] Fetching messages for session: {session_id}")
    
    try:
        # Verify session belongs to user
        session = await session_repo.get_user_session(session_id, str(current_user["_id"]))
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages
        messages = await message_repo.get_session_messages(session_id)
        
        # Convert to response models
        message_list = []
        for msg in messages:
            message_response = convert_message_to_response(msg)
            message_list.append(message_response.dict())
        
        session_response = convert_session_to_response(session)
        
        print(f"[SESSION] Fetched {len(message_list)} messages in {time.time() - start_time:.2f}s")
        
        return ChatHistoryResponse(
            session=session_response,
            messages=message_list
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SESSION] Error fetching messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")


@session_router.delete("/{session_id}")
async def delete_session(session_id: str, current_user = Depends(get_current_user)):
    """Delete a session and all its messages."""
    start_time = time.time()
    print(f"\n[SESSION] Deleting session: {session_id}")
    
    try:
        # Delete session
        deleted = await session_repo.delete_session(session_id, str(current_user["_id"]))
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Delete all messages
        deleted_messages = await message_repo.delete_session_messages(session_id)
        
        print(f"[SESSION] Session deleted with {deleted_messages} messages in {time.time() - start_time:.2f}s")
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SESSION] Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@session_router.post("/{session_id}/update")
async def update_session(session_id: str, request: Request, current_user = Depends(get_current_user)):
    """Update a session (e.g., title)."""
    start_time = time.time()
    print(f"\n[SESSION] Updating session: {session_id}")
    try:
        payload = await request.json()
        title = payload.get("title")
        if title is not None:
            title = str(title).strip()
            if len(title) == 0:
                raise HTTPException(status_code=400, detail="Title cannot be empty")
            # Trim overly long titles
            if len(title) > 80:
                title = title[:77] + "..."

        # Verify session belongs to user
        session = await session_repo.get_user_session(session_id, str(current_user["_id"]))
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Build update fields
        update_fields = {"updated_at": datetime.utcnow()}
        if title is not None:
            update_fields["title"] = title

        # Persist changes
        await session_repo.update_session(session_id, **update_fields)

        print(f"[SESSION] Updated in {time.time() - start_time:.2f}s")
        return {"success": True, "session_id": session_id, "updated": update_fields}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SESSION] Error updating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")


# ==================== DOCUMENT UPLOAD ROUTES ====================

@upload_router.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), current_user = Depends(get_current_user)):
    """Handle PDF file uploads."""
    start_time = time.time()
    print(f"\n[UPLOAD] User {current_user['username']} uploading: {file.filename}")
    
    try:
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        t0 = time.time()
        content = await file.read()
        print(f"[UPLOAD] File read in {time.time() - t0:.2f}s ({len(content)} bytes)")
        
        # Check file size
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File size must be less than {settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Generate unique identifier
        file_id = f"upload_{int(time.time())}_{current_user['username']}_{file.filename}"
        
        # Store in upload directory
        upload_path = os.path.join(settings.UPLOAD_DIR, file_id)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        t1 = time.time()
        with open(upload_path, "wb") as f:
            f.write(content)
        print(f"[UPLOAD] File saved to {upload_path} in {time.time() - t1:.2f}s")
        
        print(f"[UPLOAD] Total upload time: {time.time() - start_time:.2f}s")
        
        return UploadResponse(
            success=True,
            file_id=file_id,
            filename=file.filename,
            message="PDF uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[UPLOAD] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


# ==================== CHAT AND RAG ROUTES ====================

@chat_router.post("/chat")
async def chat_endpoint(
    question: str = Form(...),
    session_id: str = Form(...),
    current_user = Depends(get_current_user)
):
    """
    Multi-Agentic RAG Chat Endpoint
    Processes user questions through the multi-agent system.
    """
    overall_start = time.time()
    print(f"\n{'='*80}")
    print(f"[CHAT] User: {current_user['username']} | Session: {session_id}")
    print(f"[CHAT] Question: {question}")
    print(f"{'='*80}")
    
    try:
        # Verify session belongs to user
        session = await session_repo.get_user_session(session_id, str(current_user["_id"]))
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        print(f"[CHAT] Session found - Document ID: {session.get('document_id')}, Document URL: {session.get('document_url')}")
        
        # Check if this is the first question (for session naming)
        message_count = await message_repo.get_session_message_count(session_id)
        is_first_question = message_count == 0
        
        # Save user message
        from ..models import MessageDocument
        user_message = MessageDocument(
            session_id=session_id,
            type="user",
            content=question,
            created_at=datetime.utcnow()
        )
        await message_repo.create_message(user_message)
        
        # Auto-rename session if it's the first question
        if is_first_question:
            from ..utils.session_namer import session_namer
            # Generate title from question only, no document name clutter
            new_title = session_namer.generate_session_title(question)
            
            # Update session title using the update_session method
            await session_repo.update_session(session_id, title=new_title, updated_at=datetime.utcnow())
            print(f"[CHAT] Auto-named session: {new_title}")
        
        # Determine document source
        doc_source = None
        is_local_file = False
        
        if session.get("document_id"):
            doc_source = os.path.join(settings.UPLOAD_DIR, session["document_id"])
            is_local_file = True
            print(f"[CHAT] Document source (local file): {doc_source}")
        elif session.get("document_url"):
            doc_source = session["document_url"]
            is_local_file = False
            print(f"[CHAT] Document source (URL): {doc_source}")
        else:
            raise HTTPException(status_code=400, detail="No document associated with session")
        
        # Process through multi-agent system
        from ..document_processing import document_processor
        if document_processor is None:
            raise HTTPException(status_code=500, detail="Document processor not initialized")
        
        rag_system = MultiAgentRAGSystem(auth_service.client, document_processor)
        result = await rag_system.process_question(question, session_id, doc_source, is_local_file)
        
        # Save bot message
        bot_message = MessageDocument(
            session_id=session_id,
            type="bot",
            content=result["answer"],
            processing_time=result["processing_time"],
            created_at=datetime.utcnow(),
            metadata=result["metadata"]
        )
        await message_repo.create_message(bot_message)
        
        # Update session
        await session_repo.increment_message_count(session_id, 2)
        await session_repo.update_session(session_id, updated_at=datetime.utcnow())
        
        # Include session title in response if it was just renamed
        response_data = JSONResponse(result)
        if is_first_question:
            response_data.headers["X-Session-Title"] = new_title
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CHAT] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


# ==================== LEGACY COMPATIBILITY ROUTES ====================

@legacy_router.post("/hackrx/run")
async def hackrx_run(request: QueryRequest, authorization: str = Header(None)):
    """Original endpoint for backward compatibility."""
    start_time = time.time()
    
    try:
        # Log request
        log_entry = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "auth_header": authorization,
            "request_data": request.dict()
        }
        await log_repo.create_log_from_request(**log_entry)
        
        # Process document
        doc_url = request.documents
        chunks, faiss_index = await document_processor.get_or_process_document(doc_url, is_local_file=False)
        
        # Process questions
        tasks = [answer_question_simple(q, chunks, faiss_index) for q in request.questions]
        answers = await asyncio.gather(*tasks)
        
        print(f"[LEGACY] Overall API call time: {time.time() - start_time:.2f}s")
        return {"answers": answers}
        
    except Exception as e:
        print(f"[LEGACY] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


async def answer_question_simple(question: str, chunks: list, faiss_index) -> str:
    """Simple answer for backward compatibility."""
    from ..document_processing import (
        get_embeddings, search_faiss, rerank_chunks_by_keyword_overlap
    )
    
    # Expand question semantics
    synonyms = {
        "IVF": ["in vitro fertilization", "assisted reproduction", "ART", "infertility treatment"],
        "settled": ["paid", "reimbursed", "processed"],
        "hospitalization": ["hospital admission", "inpatient care"],
        "SQL": ["structured query language", "database query", "SQL statement"],
        "query": ["queries", "statement", "command"],
    }
    
    expanded = [question]
    for term, alts in synonyms.items():
        if term.lower() in question.lower():
            for alt in alts:
                expanded.append(question.replace(term, alt))
    
    # Generate embeddings and search
    question_embeddings = await get_embeddings(expanded, auth_service.client)
    import numpy as np
    avg_embedding = np.mean(question_embeddings, axis=0, keepdims=True)
    
    # Initial retrieval using configured top_k
    retrieved_chunks = search_faiss(avg_embedding, faiss_index, chunks, k=None)
    top_chunks = rerank_chunks_by_keyword_overlap(question, retrieved_chunks, top_k=None)
    
    # If limited context, expand search window and combine
    from ..config import settings as _settings
    if len(top_chunks) < min(10, _settings.RETRIEVAL_TOP_K):
        expanded_k = min(len(chunks), _settings.RETRIEVAL_TOP_K * 3)
        retrieved_more = search_faiss(avg_embedding, faiss_index, chunks, k=expanded_k)
        reranked_more = rerank_chunks_by_keyword_overlap(question, retrieved_more, top_k=expanded_k)
        seen = set()
        combined = []
        for c in (top_chunks + reranked_more):
            if c not in seen:
                seen.add(c)
                combined.append(c)
        top_chunks = combined[: _settings.RETRIEVAL_TOP_K]
    context = "\n---\n".join(top_chunks)
    
    # Generate answer
    prompt = f"""Answer this question based on the document context provided.
Keep the answer concise (1-2 sentences) and use keywords from the document.

Context:
{context}

Question: {question}
Answer:"""
    
    response = await auth_service.client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=300,
        model=settings.OPENAI_DEPLOYMENT
    )
    
    return response.choices[0].message.content.strip()


# ==================== HTML PAGES ====================

@chat_router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    from fastapi.templating import Jinja2Templates
    
    templates = Jinja2Templates(directory="app/templates")
    return templates.TemplateResponse("index.html", {"request": request})


# ==================== HEALTH CHECK ====================

@auth_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "app_name": settings.APP_NAME
    }


# Function to include all routers in main app
def include_routers(app):
    """Include all API routers in the FastAPI app."""
    app.include_router(auth_router)
    app.include_router(session_router)
    app.include_router(upload_router)
    app.include_router(chat_router)
    app.include_router(legacy_router)
    app.include_router(flashcards_router)
    
    print("[API] All routers included successfully")
