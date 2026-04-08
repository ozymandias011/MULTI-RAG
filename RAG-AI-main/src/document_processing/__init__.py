"""
Document processing module for MULRAG application.

This module handles PDF text extraction, text chunking, embedding generation,
and FAISS indexing for document retrieval and RAG operations.
"""

import asyncio
import io
import os
import time
from typing import List, Tuple, Any, Dict
import numpy as np
import faiss
import fitz  # PyMuPDF
import httpx
from openai import AsyncAzureOpenAI

from ..config import settings


class DocumentProcessor:
    """Main document processing class."""
    
    def __init__(self, client: AsyncAzureOpenAI):
        """Initialize document processor."""
        self.client = client
        self.document_cache = {}  # {doc_source: (chunks, faiss_index)}
        print("[DOC] Document processor initialized")
    
    async def get_or_process_document(self, doc_source: str, is_local_file: bool) -> Tuple[List[str], Any]:
        """Get document from cache or process if not cached."""
        # Check cache first
        if doc_source in self.document_cache:
            print("[DOC] Using cached document embeddings")
            chunks, faiss_index = self.document_cache[doc_source]
            # Update last accessed time
            self.document_cache[doc_source] = (chunks, faiss_index)
            return chunks, faiss_index
        
        print("[DOC] Processing document for first time...")
        
        # Extract text
        text = await self._extract_text(doc_source, is_local_file)
        print(f"[DOC] Extracted {len(text)} characters")
        
        # Validate extracted text
        if not text or len(text.strip()) < 50:
            raise ValueError(f"Document extraction failed or document is too short. Extracted {len(text)} characters.")
        
        # Chunk text
        chunks = self._chunk_text(text)
        print(f"[DOC] Created {len(chunks)} chunks")
        
        # Validate chunks
        if not chunks:
            raise ValueError("No valid chunks created from document. Document may be empty or corrupted.")
        
        # Generate embeddings
        embeddings = await self._generate_embeddings(chunks)
        print(f"[DOC] Generated {len(embeddings)} embeddings")
        
        # Validate embeddings
        if len(embeddings) == 0:
            raise ValueError("Failed to generate embeddings from document chunks.")
        
        # Create FAISS index
        faiss_index = self._create_faiss_index(embeddings)
        print(f"[DOC] Created FAISS index")
        
        # Cache results
        self.document_cache[doc_source] = (chunks, faiss_index)
        print("[DOC] Document cached for future queries")
        
        return chunks, faiss_index
    
    async def _extract_text(self, doc_source: str, is_local_file: bool) -> str:
        """Extract text from PDF file or URL."""
        start_time = time.time()
        
        try:
            if is_local_file:
                # Verify file exists
                if not os.path.exists(doc_source):
                    raise FileNotFoundError(f"File not found: {doc_source}")
                
                print(f"[DOC] Extracting text from local PDF: {doc_source}")
                text = await self._extract_text_from_local(doc_source)
            else:
                print(f"[DOC] Downloading and extracting text from URL: {doc_source}")
                text = await self._extract_text_from_url(doc_source)
            
            print(f"[DOC] Text extraction completed in {time.time() - start_time:.2f}s")
            return text
            
        except Exception as e:
            print(f"[DOC] Text extraction error: {str(e)}")
            raise
    
    async def _extract_text_from_local(self, file_path: str) -> str:
        """Extract text from local PDF file."""
        def extract_text():
            try:
                with fitz.open(file_path) as doc:
                    text = "\n".join(page.get_text() for page in doc)
                    
                    # Check if we got meaningful text
                    if len(text.strip()) < 50:
                        print(f"[DOC] Warning: Extracted only {len(text)} characters from PDF")
                        print(f"[DOC] This might be a scanned PDF. Consider using OCR or a text-based PDF.")
                        print(f"[DOC] First 100 chars: {repr(text[:100])}")
                        
                        # Try to extract with different methods
                        all_text = ""
                        for page_num in range(len(doc)):
                            page = doc[page_num]
                            # Try different text extraction methods
                            page_text = page.get_text()
                            if not page_text.strip():
                                # Try get_text("blocks") method
                                try:
                                    blocks = page.get_text("blocks")
                                    if blocks:
                                        page_text = "\n".join([block[4] for block in blocks if block[4].strip()])
                                except:
                                    page_text = ""
                            
                            all_text += page_text + "\n"
                        
                        text = all_text
                    
                    return text
                    
            except Exception as e:
                print(f"[DOC] Error extracting text from PDF: {str(e)}")
                raise ValueError(f"Failed to extract text from PDF: {str(e)}")
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, extract_text)
    
    async def _extract_text_from_url(self, pdf_url: str) -> str:
        """Extract text from PDF URL."""
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(pdf_url, timeout=30.0)
            response.raise_for_status()
        
        pdf_file_stream = io.BytesIO(response.content)
        
        def extract_text():
            with fitz.open(stream=pdf_file_stream, filetype="pdf") as doc:
                return "\n".join(page.get_text() for page in doc)
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, extract_text)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Smart text chunking with paragraph awareness."""
        # Clean and normalize text first
        text = text.strip()
        if not text:
            return []
        
        # Split by paragraphs first
        paras = [p.strip() for p in text.split('\n') if p.strip()]
        
        # If no paragraphs, try to split by sentences or just use the whole text
        if not paras:
            import re
            # Try sentence splitting
            sentences = re.split(r'[.!?]+', text)
            paras = [s.strip() for s in sentences if s.strip()]
        
        # If still no paragraphs, use the whole text as one chunk
        if not paras:
            paras = [text]
        
        chunks, buffer = [], ""
        
        for p in paras:
            if len(buffer) + len(p) < settings.CHUNK_SIZE:
                buffer += " " + p if buffer else p
            else:
                if buffer:
                    chunks.append(buffer.strip())
                buffer = p
        
        if buffer:
            chunks.append(buffer.strip())
        
        # Filter out very small chunks and ensure we have at least some chunks
        filtered_chunks = [c for c in chunks if len(c.split()) > settings.MIN_CHUNK_WORDS]
        
        # If filtering removed all chunks, return the original chunks
        if not filtered_chunks and chunks:
            print(f"[DOC] Warning: All chunks were filtered out, using original {len(chunks)} chunks")
            return chunks
        
        return filtered_chunks
    
    async def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts in batches."""
        start_time = time.time()
        
        all_embeddings = []
        batch_size = settings.EMBEDDING_BATCH_SIZE
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.client.embeddings.create(
                input=batch, 
                model=settings.OPENAI_EMBEDDING_DEPLOYMENT
            )
            all_embeddings.extend([item.embedding for item in response.data])
        
        embeddings = np.array(all_embeddings, dtype=np.float32)
        print(f"[DOC] Embedding generation completed in {time.time() - start_time:.2f}s")
        
        return embeddings
    
    def _create_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """Create FAISS index from embeddings."""
        start_time = time.time()
        
        # Validate embeddings
        if embeddings is None or len(embeddings) == 0:
            raise ValueError("Cannot create FAISS index: No embeddings provided")
        
        embedding_dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(embedding_dim)
        index.add(embeddings)
        
        print(f"[DOC] FAISS index creation completed in {time.time() - start_time:.2f}s")
        print(f"[DOC] Index dimension: {embedding_dim}")
        print(f"[DOC] Index size: {index.ntotal} vectors")
        
        return index
    
    def clear_cache(self):
        """Clear document cache."""
        self.document_cache.clear()
        print("[DOC] Cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information."""
        return {
            "cached_documents": len(self.document_cache),
            "cache_keys": list(self.document_cache.keys())
        }


class TextProcessor:
    """Utility class for text processing operations."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\n]', '', text)
        return text.strip()
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction based on word frequency
        words = text.lower().split()
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must'}
        
        filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in keywords[:max_keywords]]
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calculate simple similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)


class EmbeddingManager:
    """Manager for embedding operations."""
    
    def __init__(self, client: AsyncAzureOpenAI):
        """Initialize embedding manager."""
        self.client = client
    
    async def get_embeddings(self, texts: List[str], model: str = None) -> np.ndarray:
        """Generate embeddings for texts."""
        if model is None:
            model = settings.OPENAI_EMBEDDING_DEPLOYMENT
        
        all_embeddings = []
        batch_size = settings.EMBEDDING_BATCH_SIZE
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.client.embeddings.create(
                input=batch, 
                model=model
            )
            all_embeddings.extend([item.embedding for item in response.data])
        
        return np.array(all_embeddings, dtype=np.float32)
    
    async def get_single_embedding(self, text: str, model: str = None) -> np.ndarray:
        """Generate embedding for a single text."""
        if model is None:
            model = settings.OPENAI_EMBEDDING_DEPLOYMENT
        
        response = await self.client.embeddings.create(input=[text], model=model)
        return np.array(response.data[0].embedding, dtype=np.float32)
    
    @staticmethod
    def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings."""
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class SearchManager:
    """Manager for search operations."""
    
    @staticmethod
    def search_faiss(query_embedding: np.ndarray, index: faiss.Index, chunks: List[str], k: int = None) -> List[str]:
        """Search FAISS index for similar chunks with dynamic cap."""
        if k is None:
            from ..config import settings as _settings
            k = _settings.RETRIEVAL_TOP_K
        k = min(k, len(chunks))
        distances, indices = index.search(query_embedding, k)
        return [chunks[i] for i in indices[0] if 0 <= i < len(chunks)]
    
    @staticmethod
    def rerank_chunks_by_keyword_overlap(question: str, chunks: List[str], top_k: int = None) -> List[str]:
        """Rerank chunks by keyword overlap with question, cap by list size."""
        if top_k is None:
            from ..config import settings as _settings
            top_k = _settings.RETRIEVAL_TOP_K
        q_words = set(question.lower().split())
        ranked = sorted(chunks, key=lambda c: sum(w in c.lower() for w in q_words), reverse=True)
        return ranked[: min(top_k, len(ranked))]
    
    @staticmethod
    def hybrid_search(
        question: str, 
        query_embedding: np.ndarray, 
        index: faiss.Index, 
        chunks: List[str], 
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        top_k: int = 21
    ) -> List[str]:
        """Hybrid search combining semantic and keyword matching."""
        # Semantic search
        semantic_chunks = SearchManager.search_faiss(query_embedding, index, chunks, k=top_k * 2)
        
        # Keyword search
        keyword_chunks = SearchManager.rerank_chunks_by_keyword_overlap(question, chunks, top_k * 2)
        
        # Combine scores
        chunk_scores = {}
        
        # Semantic scores
        for i, chunk in enumerate(semantic_chunks):
            chunk_scores[chunk] = chunk_scores.get(chunk, 0) + semantic_weight * (1.0 - i / len(semantic_chunks))
        
        # Keyword scores
        for i, chunk in enumerate(keyword_chunks):
            chunk_scores[chunk] = chunk_scores.get(chunk, 0) + keyword_weight * (1.0 - i / len(keyword_chunks))
        
        # Sort by combined scores
        ranked_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)
        return [chunk for chunk, score in ranked_chunks[:top_k]]


# Global instances (will be initialized in main app)
document_processor: DocumentProcessor = None
embedding_manager: EmbeddingManager = None
search_manager: SearchManager = SearchManager()


def initialize_document_processing(client: AsyncAzureOpenAI):
    """Initialize global document processing instances."""
    global document_processor, embedding_manager
    
    document_processor = DocumentProcessor(client)
    embedding_manager = EmbeddingManager(client)
    
    print("[DOC] Document processing module initialized")


# Export functions for use in other modules
async def get_embeddings(texts: List[str], client: AsyncAzureOpenAI, model: str = None) -> np.ndarray:
    """Get embeddings for texts."""
    if embedding_manager is None:
        raise RuntimeError("Embedding manager not initialized")
    
    if model is None:
        model = settings.OPENAI_EMBEDDING_DEPLOYMENT
    
    return await embedding_manager.get_embeddings(texts, model)


async def extract_text_from_pdf_local(file_path: str) -> str:
    """Extract text from locally stored PDF."""
    if document_processor is None:
        raise RuntimeError("Document processor not initialized")
    
    return await document_processor._extract_text_from_local(file_path)


async def extract_text_from_pdf_fast(pdf_url: str) -> str:
    """Extract text from PDF URL."""
    if document_processor is None:
        raise RuntimeError("Document processor not initialized")
    
    return await document_processor._extract_text_from_url(pdf_url)


def smart_chunk_text(text: str, max_len: int = None) -> List[str]:
    """Smart text chunking with paragraph awareness."""
    if max_len is None:
        max_len = settings.CHUNK_SIZE
    
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    chunks, buffer = [], ""
    
    for p in paras:
        if len(buffer) + len(p) < max_len:
            buffer += " " + p
        else:
            if buffer:
                chunks.append(buffer.strip())
            buffer = p
    
    if buffer:
        chunks.append(buffer.strip())
    
    return [c for c in chunks if len(c.split()) > settings.MIN_CHUNK_WORDS]


def search_faiss(query_embedding: np.ndarray, index: faiss.Index, chunks: List[str], k: int = None) -> List[str]:
    """Search FAISS index for similar chunks."""
    if k is None:
        k = settings.RETRIEVAL_TOP_K
    
    return search_manager.search_faiss(query_embedding, index, chunks, k)


def rerank_chunks_by_keyword_overlap(question: str, chunks: List[str], top_k: int = None) -> List[str]:
    """Rerank chunks by keyword overlap with question."""
    if top_k is None:
        top_k = settings.RETRIEVAL_TOP_K
    
    return search_manager.rerank_chunks_by_keyword_overlap(question, chunks, top_k)
