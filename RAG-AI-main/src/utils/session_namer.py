"""
Session naming utilities for MULRAG application.

This module provides intelligent session naming based on user questions
and document content to improve user experience.
"""

import re
from typing import Optional


class SessionNamer:
    """Utility class for generating intelligent session names."""
    
    # Common stop words to filter out
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
        'am', 'its', 'it', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours',
        'you', 'your', 'yours', 'he', 'him', 'his', 'she', 'her', 'hers',
        'they', 'them', 'their', 'theirs', 'about', 'into', 'through',
        'during', 'before', 'after', 'above', 'below', 'between', 'under',
        'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
        'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
        'too', 'very', 'just', 'also', 'now', 'tell', 'say', 'know', 'get',
        'give', 'go', 'make', 'see', 'come', 'take', 'want', 'look', 'use',
        'find', 'give', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave',
        'call', 'keep', 'let', 'begin', 'show', 'hear', 'play', 'run', 'move',
        'like', 'live', 'believe', 'hold', 'bring', 'happen', 'write', 'provide',
        'sit', 'stand', 'lose', 'pay', 'meet', 'include', 'continue', 'set',
        'learn', 'change', 'lead', 'understand', 'watch', 'follow', 'stop',
        'create', 'speak', 'read', 'allow', 'add', 'spend', 'grow', 'open',
        'walk', 'win', 'offer', 'remember', 'love', 'consider', 'appear',
        'buy', 'wait', 'serve', 'die', 'send', 'expect', 'build', 'stay',
        'fall', 'cut', 'reach', 'kill', 'remain', 'please', 'explain',
        'describe', 'regarding', 'related', 'concerning'
    }
    
    @staticmethod
    def generate_session_title(question: str, document_name: Optional[str] = None) -> str:
        """
        Generate a short, meaningful session title from the user's question.
        Extracts only the core topic (1-3 key words), no filler.
        
        Args:
            question: User's first question about the document
            document_name: Name of the uploaded document (optional)
            
        Returns:
            A very concise session title (just the topic)
        """
        # Extract core topic from the question
        title = SessionNamer._extract_core_topic(question)
        
        # Capitalize nicely
        if title:
            title = title.title()
        else:
            title = "Chat"
        
        # Hard cap at 30 chars for brevity
        if len(title) > 30:
            title = title[:27] + "..."
        
        return title
    
    @staticmethod
    def _extract_core_topic(question: str) -> str:
        """
        Extract the core topic (1-3 meaningful words) from a question.
        E.g., "what are the room charges" -> "room charges"
        """
        # Clean input
        text = question.strip().lower()
        
        # Remove punctuation except hyphens within words
        text = re.sub(r'[^\w\s-]', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Filter out stop words and short words
        meaningful = [
            w for w in words
            if w not in SessionNamer.STOP_WORDS and len(w) > 2
        ]
        
        # Take up to 3 meaningful words
        topic_words = meaningful[:3]
        
        if topic_words:
            return " ".join(topic_words)
        else:
            # Fallback: take first 2 non-trivial words
            fallback = [w for w in words if len(w) > 2][:2]
            return " ".join(fallback) if fallback else ""
    
    @staticmethod
    def _extract_document_topics(document_name: Optional[str]) -> str:
        """Extract topics from document name."""
        if not document_name:
            return ""
        
        # Remove file extension and common prefixes
        name = re.sub(r'\.(pdf|docx?|txt)$', '', document_name, flags=re.IGNORECASE)
        name = re.sub(r'^(upload_|file_|doc_|\d+_)', '', name, flags=re.IGNORECASE)
        
        # Extract key terms
        words = re.findall(r'\b[a-zA-Z]+\b', name)
        key_terms = [w for w in words if w.lower() not in SessionNamer.STOP_WORDS and len(w) > 2]
        
        return " ".join(key_terms[:2])
    
    @staticmethod
    def update_session_title(session_id: str, question: str, document_name: Optional[str] = None) -> str:
        """
        Update session title and return the new title.
        
        Args:
            session_id: ID of the session to update
            question: User's question
            document_name: Document name (optional)
            
        Returns:
            The new session title
        """
        # Generate new title
        new_title = SessionNamer.generate_session_title(question, document_name)
        
        print(f"[SESSION] Updated session {session_id} title to: {new_title}")
        return new_title


# Global instance
session_namer = SessionNamer()
