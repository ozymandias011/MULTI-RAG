# src/flashcards/service.py
"""
Flashcards service for MULRAG — generates concise fact-cards from a processed document.
This implementation uses the existing `src.document_processing` module (document_processor,
embedding_manager, TextProcessor, search_faiss). It is built to be an MVP:
- deterministic (no LLM)
- uses chunk embeddings for ranking & dedupe
- returns short, traceable fact cards
"""

import re
from typing import List, Dict, Any, Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import from your existing document_processing implementation
from src.document_processing import (
    document_processor,
    embedding_manager,
    TextProcessor,
    search_faiss,
)

router = APIRouter(prefix="/api/v1/flashcards", tags=["flashcards"])


# -------------------- Utilities --------------------
def _clean_text_snippet(text: str, max_len: int = 300) -> str:
    t = text.strip()
    if len(t) <= max_len:
        return t
    # truncate gracefully
    return t[: max_len - 3].rstrip() + "..."


def _def_boost_score(text: str) -> float:
    """Return 1.0 if text looks like a definition/fact sentence."""
    return 1.0 if re.search(r"\b(is|are|was|created|developed|used for|consists of|includes|refers to)\b", text, re.I) else 0.0


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None:
        return 0.0
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _dedupe_by_embedding(candidates: List[Dict[str, Any]], threshold: float = 0.85, max_keep: int = 10) -> List[Dict[str, Any]]:
    """Keep top candidates while deduplicating by embedding cosine similarity."""
    kept: List[Dict[str, Any]] = []
    kept_embs: List[np.ndarray] = []
    for c in candidates:
        emb = c.get("embedding")
        if emb is None:
            # fallback: keep short-list if embeddings missing
            if len(kept) < max_keep:
                kept.append(c)
            continue
        emb_arr = np.asarray(emb, dtype=float)
        similar = False
        for ke in kept_embs:
            if _cosine_sim(emb_arr, ke) >= threshold:
                similar = True
                break
        if not similar:
            kept.append(c)
            kept_embs.append(emb_arr)
        if len(kept) >= max_keep:
            break
    return kept


def _normalize_list(values: List[float]) -> List[float]:
    if not values:
        return []
    arr = np.array(values, dtype=float)
    mn, mx = arr.min(), arr.max()
    if mn == mx:
        return [0.5 for _ in values]
    return ((arr - mn) / (mx - mn)).tolist()


# -------------------- Core generation --------------------
async def generate_flashcards_for_document(
    document_source: str,
    is_local_file: bool = False,
    count: int = 10,
    candidate_pool_k: int = 200,
) -> List[Dict[str, Any]]:
    """
    Generate a list of fact-cards from a document.
    Returns: [{id, title, content, source_chunk_index}]
    """
    if document_processor is None or embedding_manager is None:
        raise RuntimeError("document_processing not initialized. Call initialize_document_processing(client) at app startup.")

    # 1) Ensure document processed (chunks, faiss_index)
    chunks, faiss_index = await document_processor.get_or_process_document(document_source, is_local_file)
    if not chunks:
        return []

    # chunks: List[str] (assumes your get_or_process_document returns plain strings)
    n_chunks = len(chunks)

    # 2) Compute or fetch embeddings for chunks
    # embedding_manager.get_embeddings returns np.ndarray shape (n, dim)
    embeddings = await embedding_manager.get_embeddings(chunks)
    if embeddings is None or len(embeddings) == 0:
        raise RuntimeError("Failed to generate embeddings for document chunks")

    # 3) Centrality score: similarity to document centroid
    centroid = np.mean(embeddings, axis=0)
    cent_scores = [_cosine_sim(embeddings[i], centroid) for i in range(n_chunks)]

    # 4) Keyword/entity frequency score: extract keywords from whole doc text
    doc_text = " ".join(chunks)
    keywords = TextProcessor.extract_keywords(doc_text, max_keywords=200)
    kw_counts: Dict[str, int] = {}
    doc_words = doc_text.lower().split()
    for kw in keywords:
        kw_counts[kw] = doc_words.count(kw.lower())

    ent_scores = []
    for chunk_text in chunks:
        low = chunk_text.lower()
        max_ct = 0
        for kw, cnt in kw_counts.items():
            if kw.lower() in low and cnt > max_ct:
                max_ct = cnt
        ent_scores.append(float(max_ct))

    # 5) Definition/fact pattern boost
    def_boosts = [_def_boost_score(c) for c in chunks]

    # 6) Normalize & combine scores
    norm_cent = _normalize_list(cent_scores)
    norm_ent = _normalize_list(ent_scores)
    combined_scores = []
    for i in range(n_chunks):
        r = norm_cent[i] if i < len(norm_cent) else 0.0
        e = norm_ent[i] if i < len(norm_ent) else 0.0
        d = def_boosts[i] if i < len(def_boosts) else 0.0
        # weights tuned for MVP: centrality 0.5, keyword freq 0.3, def boost 0.2
        combined_scores.append(0.5 * r + 0.3 * e + 0.2 * d)

    # 7) Build candidate objects and sort
    candidates: List[Dict[str, Any]] = []
    for i, text in enumerate(chunks):
        candidates.append(
            {
                "idx": i,
                "text": text,
                "embedding": np.asarray(embeddings[i], dtype=float),
                "score_final": combined_scores[i],
            }
        )

    candidates.sort(key=lambda x: x.get("score_final", 0.0), reverse=True)

    # Keep a reasonable pool for dedupe (cap)
    pool_k = max(50, min(candidate_pool_k, len(candidates)))
    candidates = candidates[:pool_k]

    # 8) Deduplicate semantically and keep top `count`
    kept = _dedupe_by_embedding(candidates, threshold=0.85, max_keep=count)

    # 9) Convert into flashcard objects
    flashcards: List[Dict[str, Any]] = []
    for c in kept:
        idx = c["idx"]
        text = chunks[idx]
        # Title: use top keywords from the chunk or first words as fallback
        chunk_keywords = TextProcessor.extract_keywords(text, max_keywords=5)
        title = chunk_keywords[0].title() if chunk_keywords else " ".join(text.split()[:6])
        flashcards.append(
            {
                "id": f"{document_source}::chunk::{idx}",
                "title": title,
                "content": _clean_text_snippet(text, max_len=300),
                "source_chunk_index": idx,
            }
        )

    return flashcards


# -------------------- FastAPI endpoint --------------------
class FlashcardRequest(BaseModel):
    document_source: str
    is_local_file: Optional[bool] = False
    count: Optional[int] = 10


@router.post("/", summary="Generate fact-based flashcards from a document (file path or URL)")
async def flashcards_endpoint(req: FlashcardRequest):
    if not req.document_source:
        raise HTTPException(status_code=400, detail="document_source is required")
    try:
        cards = await generate_flashcards_for_document(
            document_source=req.document_source,
            is_local_file=bool(req.is_local_file),
            count=int(req.count or 10),
        )
        return {"flashcards": cards}
    except Exception as e:
        # keep error message concise for API; for debugging logs, print stack in server logs
        raise HTTPException(status_code=500, detail=str(e))