"""
Multi-Agent RAG system for MULRAG application.

This module implements the multi-agent architecture for document-based question answering.
Agents include:
1. Question Understanding Agent - Analyzes and rephrases questions
2. History Analysis Agent - Analyzes chat history for context
3. Context Retrieval Agent - Retrieves relevant document chunks
4. Answer Generation Agent - Generates final responses
"""

import time
from typing import List, Dict, Any, Tuple
from openai import AsyncAzureOpenAI

from ..config import settings
from ..models import QuestionUnderstanding, ChatContext, AgentResult
from ..database import message_repo


class BaseAgent:
    """Base class for all RAG agents."""
    
    def __init__(self, client: AsyncAzureOpenAI):
        """Initialize base agent."""
        self.client = client
        self.model = settings.OPENAI_DEPLOYMENT
    
    async def _call_llm(self, prompt: str, temperature: float = 0.1, max_tokens: int = 2000) -> str:
        """Generic LLM call method."""
        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                model=self.model
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[AGENT] LLM call failed: {str(e)}")
            raise
    
    def _measure_time(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure execution time of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time


class QuestionUnderstandingAgent(BaseAgent):
    """Agent 1: Understands questions and determines intent."""
    
    def __init__(self, client: AsyncAzureOpenAI):
        """Initialize question understanding agent."""
        super().__init__(client)
        self.agent_name = "Question Understanding Agent"
    
    async def process_question(self, question: str) -> AgentResult:
        """Process and understand the user's question."""
        start_time = time.time()
        print(f"[{self.agent_name}] Starting analysis...")
        
        try:
            # Create prompt for question understanding
            prompt = f"""You are a Question Understanding Agent.
Analyze the user's question and return JSON only with fields:
{{
    "understood": "rephrased question",
    "intent": "one of: factual_query | clarification | follow_up | comparison | summarization | instruction | multi_part | opinion | troubleshooting",
    "confidence": 0-1 float
}}

Rules:
- Prefer "follow_up" if it references prior context (pronouns like it/that/these, or mentions previous answers)
- Use "clarification" when asking to explain or elaborate
- Use "comparison" when contrasting entities (vs, difference)
- Use "summarization" when asking for an overview or summary
- Use "instruction" when asking for steps/how-to/procedure
- Use "troubleshooting" for error/issue fixing
- Use "multi_part" for compound questions with multiple asks
- Otherwise "factual_query".

Question: {question}

Return ONLY the JSON string with keys exactly as specified."""
            
            # Call LLM
            response = await self._call_llm(prompt, temperature=0.0, max_tokens=150)
            
            # Parse JSON response
            understood_question, intent = self._parse_response_json(response, question)
            
            processing_time = time.time() - start_time
            print(f"[{self.agent_name}] Completed in {processing_time:.2f}s")
            print(f"[{self.agent_name}] Understood: {understood_question}")
            print(f"[{self.agent_name}] Intent: {intent}")
            
            return AgentResult(
                agent_name=self.agent_name,
                processing_time=processing_time,
                result=QuestionUnderstanding(
                    understood_question=understood_question,
                    intent=intent
                )
            )
            
        except Exception as e:
            print(f"[{self.agent_name}] Error: {str(e)}")
            raise
    
    def _parse_response_json(self, response: str, original_question: str) -> Tuple[str, str]:
        """Parse JSON response safely and fall back to defaults."""
        import json
        understood = original_question
        intent = "factual_query"
        try:
            # Extract JSON block if extra text present
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                obj = json.loads(response[start:end+1])
            else:
                obj = json.loads(response)
            u = obj.get('understood')
            i = obj.get('intent')
            if isinstance(u, str) and len(u.strip()) > 0:
                understood = u.strip()
            if isinstance(i, str) and len(i.strip()) > 0:
                intent = i.strip()
        except Exception as e:
            print(f"[{self.agent_name}] JSON parse fallback: {str(e)}")
        return understood, intent


class HistoryAnalysisAgent(BaseAgent):
    """Agent 2: Analyzes chat history for relevant context."""
    
    def __init__(self, client: AsyncAzureOpenAI):
        """Initialize history analysis agent."""
        super().__init__(client)
        self.agent_name = "History Analysis Agent"
    
    async def analyze_history(self, question: str, session_id: str) -> AgentResult:
        """Analyze chat history for relevant context."""
        start_time = time.time()
        print(f"[{self.agent_name}] Starting analysis...")
        
        try:
            # Get chat history
            chat_history = await self._get_chat_history(session_id)
            
            if not chat_history or len(chat_history) < 2:
                print(f"[{self.agent_name}] Insufficient history, skipping")
                return AgentResult(
                    agent_name=self.agent_name,
                    processing_time=time.time() - start_time,
                    result=[]
                )
            
            # Format history for analysis
            history_text = self._format_history(chat_history)
            
            # Create prompt for history analysis
            prompt = f"""You are a History Analysis Agent. Determine if the current question references or relates to previous conversation.

Chat History:
{history_text}

Current Question: {question}

Does this question reference previous conversation? Answer YES or NO, then explain which parts are relevant.

Format:
REFERENCES_HISTORY: [YES/NO]
RELEVANT_CONTEXT: [brief explanation]
"""
            
            # Call LLM
            response = await self._call_llm(prompt, temperature=0.1, max_tokens=200)
            
            # Determine if history is relevant
            relevant_history = self._extract_relevant_history(response, chat_history)
            
            processing_time = time.time() - start_time
            print(f"[{self.agent_name}] Found {len(relevant_history)} relevant items in {processing_time:.2f}s")
            
            return AgentResult(
                agent_name=self.agent_name,
                processing_time=processing_time,
                result=relevant_history
            )
            
        except Exception as e:
            print(f"[{self.agent_name}] Error: {str(e)}")
            raise
    
    async def _get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        messages = await message_repo.get_recent_messages(session_id, settings.MAX_HISTORY_MESSAGES)
        
        history = []
        for msg in messages:
            history.append({
                "type": msg["type"],
                "content": msg["content"],
                "timestamp": msg["created_at"]
            })
        
        return history
    
    def _format_history(self, chat_history: List[Dict[str, Any]]) -> str:
        """Format chat history for LLM analysis."""
        return "\n".join([
            f"{msg['type'].upper()}: {msg['content']}"
            for msg in chat_history[-settings.MAX_HISTORY_EXCHANGES * 2:]  # Last N exchanges
        ])
    
    def _extract_relevant_history(self, response: str, chat_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relevant history based on LLM response."""
        if "REFERENCES_HISTORY: YES" in response:
            # Return last few relevant exchanges
            return chat_history[-settings.MAX_HISTORY_EXCHANGES * 2:]  # Last N exchanges (user + bot)
        return []


class ContextRetrievalAgent(BaseAgent):
    """Agent 3: Retrieves and processes document context."""
    
    def __init__(self, client: AsyncAzureOpenAI, document_processor):
        """Initialize context retrieval agent."""
        super().__init__(client)
        self.agent_name = "Context Retrieval Agent"
        self.document_processor = document_processor
    
    async def retrieve_context(self, question: str, understood_question: str, doc_source: str, is_local_file: bool) -> AgentResult:
        """Retrieve relevant document context."""
        start_time = time.time()
        print(f"[{self.agent_name}] Starting retrieval...")
        
        try:
            # Get or process document
            chunks, faiss_index = await self._get_document_data(doc_source, is_local_file)
            
            # Semantic search with expanded questions
            expanded_questions = self._expand_question_semantics(understood_question)
            print(f"[{self.agent_name}] Expanded question into {len(expanded_questions)} variations")
            
            # Generate embeddings for search
            from ..document_processing import get_embeddings
            question_embeddings = await get_embeddings(expanded_questions, self.client)
            avg_embedding = self._average_embeddings(question_embeddings)
            
            # First pass: hybrid search combining semantic + keyword
            from ..document_processing import search_manager
            top_chunks = search_manager.hybrid_search(
                question,
                avg_embedding,
                faiss_index,
                chunks,
                semantic_weight=0.7,
                keyword_weight=0.3,
                top_k=settings.RETRIEVAL_TOP_K
            )

            # If results are too few, progressively expand and combine
            if len(top_chunks) < min(10, settings.RETRIEVAL_TOP_K):
                expanded_k = min(len(chunks), settings.RETRIEVAL_TOP_K * 3)
                retrieved_more = self._search_faiss(avg_embedding, faiss_index, chunks, k=expanded_k)
                reranked_more = self._rerank_chunks(question, retrieved_more, top_k=expanded_k)
                seen = set()
                combined = []
                for c in (top_chunks + reranked_more):
                    if c not in seen:
                        seen.add(c)
                        combined.append(c)
                top_chunks = combined[: settings.RETRIEVAL_TOP_K]
            
            processing_time = time.time() - start_time
            print(f"[{self.agent_name}] Retrieved {len(top_chunks)} chunks in {processing_time:.2f}s")
            
            return AgentResult(
                agent_name=self.agent_name,
                processing_time=processing_time,
                result=top_chunks
            )
            
        except Exception as e:
            print(f"[{self.agent_name}] Error: {str(e)}")
            raise
    
    async def _get_document_data(self, doc_source: str, is_local_file: bool):
        """Get document chunks and FAISS index."""
        return await self.document_processor.get_or_process_document(doc_source, is_local_file)
    
    def _expand_question_semantics(self, question: str) -> List[str]:
        """Expand question with synonyms for better semantic search."""
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
        return list(set(expanded))
    
    def _average_embeddings(self, embeddings):
        """Average multiple embeddings."""
        import numpy as np
        return np.mean(embeddings, axis=0, keepdims=True)
    
    def _search_faiss(self, query_embedding, faiss_index, chunks, k: int = None):
        """Search FAISS index for similar chunks (dynamic k)."""
        if k is None:
            k = settings.RETRIEVAL_TOP_K
        k = min(k, len(chunks))
        distances, indices = faiss_index.search(query_embedding, k)
        return [chunks[i] for i in indices[0] if 0 <= i < len(chunks)]
    
    def _rerank_chunks(self, question: str, chunks: List[str], top_k: int = None) -> List[str]:
        """Rerank chunks by keyword overlap."""
        if top_k is None:
            top_k = settings.RETRIEVAL_TOP_K
        
        q_words = set(question.lower().split())
        ranked = sorted(chunks, key=lambda c: sum(w in c.lower() for w in q_words), reverse=True)
        return ranked[: min(top_k, len(ranked))]


class AnswerGenerationAgent(BaseAgent):
    """Agent 4: Generates final answers using all context."""
    
    def __init__(self, client: AsyncAzureOpenAI):
        """Initialize answer generation agent."""
        super().__init__(client)
        self.agent_name = "Answer Generation Agent"
    
    async def generate_answer(self, context: ChatContext) -> AgentResult:
        """Generate final answer using all available context."""
        start_time = time.time()
        print(f"[{self.agent_name}] Starting generation...")
        
        try:
            # Create comprehensive prompt
            prompt = self._create_answer_prompt(context)
            
            # Generate answer
            answer = await self._call_llm(prompt, temperature=0.2, max_tokens=2000)
            
            processing_time = time.time() - start_time
            print(f"[{self.agent_name}] Generated answer ({len(answer)} chars) in {processing_time:.2f}s")
            
            return AgentResult(
                agent_name=self.agent_name,
                processing_time=processing_time,
                result=answer
            )
            
        except Exception as e:
            print(f"[{self.agent_name}] Error: {str(e)}")
            raise
    
    def _create_answer_prompt(self, context: ChatContext) -> str:
        """Create comprehensive prompt for answer generation."""
        # Format document context
        doc_context_text = "\n---\n".join(context.document_context)
        
        # Format chat history
        history_context = ""
        if context.chat_history:
            history_context = "\n\nPREVIOUS CONVERSATION:\n" + "\n".join([
                f"{msg['type'].upper()}: {msg['content']}"
                for msg in context.chat_history[-6:]
            ])
        
        prompt = f"""You are an AI Assistant specializing in document analysis and question answering. You have access to:
1. The current document's relevant sections
2. Previous conversation history (if applicable)

Your task is to provide accurate, well-formatted, and contextually relevant answers.

**CRITICAL RULE**: You MUST ONLY use information from the provided document context. If the answer to the question is NOT found in the document context provided below, you MUST explicitly state:

"⚠️ **No relevant information found**: There is no information in the attached document that answers your question about [topic]. The document does not contain details regarding [specific aspect asked]."

DO NOT make assumptions or provide information from general knowledge. ONLY use what's in the document context.

FORMATTING GUIDELINES (when information IS found):
1. Use **markdown formatting** for better readability
2. Use **bold** for important terms or concepts
3. Use numbered lists (1., 2., 3.) for sequential information
4. Use bullet points (-, *) for non-sequential lists
5. Use ```sql or ```python code blocks for queries or code examples
6. Use `inline code` for short code snippets, table names, or column names
7. Break long paragraphs into smaller ones for readability

CONTENT GUIDELINES:
1. **Primary Source**: ONLY use information from the document context below
2. **Conversation Awareness**: If this is a follow-up question, reference previous answers naturally
3. **Clarity**: Be concise but comprehensive
4. **Keywords**: Use terminology from the document when possible
5. **Semantic Understanding**: Interpret related concepts intelligently, but stay within document bounds
6. **Examples**: When explaining SQL queries or code, provide formatted examples FROM THE DOCUMENT
7. **Honesty**: If information is partial or unclear, mention it explicitly

INTENT: {context.intent}
- If "follow_up": Connect to previous answers
- If "clarification": Expand on previous information with examples
- If "comparison": Use tables or lists to compare
- If "factual_query": Provide direct, well-structured information
- If "summarization": Use bullet points and sections

---
DOCUMENT CONTEXT:
{doc_context_text}
{history_context}
---

ORIGINAL QUESTION: {context.original_question}
UNDERSTOOD AS: {context.understood_question}

**Remember**: If the document context above does not contain the answer, you MUST explicitly state that no relevant information was found. Do not guess or use external knowledge.

Provide a clear, well-formatted answer using markdown:
"""
        return prompt


class MultiAgentRAGSystem:
    """Main multi-agent RAG system coordinator."""
    
    def __init__(self, client: AsyncAzureOpenAI, document_processor):
        """Initialize multi-agent system."""
        self.client = client
        self.document_processor = document_processor
        
        # Initialize agents
        self.question_agent = QuestionUnderstandingAgent(client)
        self.history_agent = HistoryAnalysisAgent(client)
        self.context_agent = ContextRetrievalAgent(client, document_processor)
        self.answer_agent = AnswerGenerationAgent(client)
    
    async def process_question(self, question: str, session_id: str, doc_source: str, is_local_file: bool) -> Dict[str, Any]:
        """Process question through all agents."""
        overall_start = time.time()
        print(f"\n{'='*80}")
        print(f"[MULTI-AGENT] Processing question for session: {session_id}")
        print(f"[MULTI-AGENT] Question: {question}")
        print(f"{'='*80}")
        
        try:
            # Agent 1: Question Understanding
            question_result = await self.question_agent.process_question(question)
            understood_question = question_result.result.understood_question
            intent = question_result.result.intent
            
            # Agent 2: History Analysis
            history_result = await self.history_agent.analyze_history(question, session_id)
            relevant_history = history_result.result
            
            # Agent 3: Context Retrieval
            context_result = await self.context_agent.retrieve_context(
                question, understood_question, doc_source, is_local_file
            )
            document_context = context_result.result
            
            # Agent 4: Answer Generation
            chat_context = ChatContext(
                original_question=question,
                understood_question=understood_question,
                intent=intent,
                document_context=document_context,
                chat_history=relevant_history
            )
            answer_result = await self.answer_agent.generate_answer(chat_context)
            answer = answer_result.result
            
            # Compile results
            total_time = time.time() - overall_start
            
            metadata = {
                "intent": intent,
                "chunks_used": len(document_context),
                "history_items": len(relevant_history),
                "agent_timings": {
                    "question_understanding": f"{question_result.processing_time:.2f}s",
                    "history_analysis": f"{history_result.processing_time:.2f}s",
                    "context_retrieval": f"{context_result.processing_time:.2f}s",
                    "answer_generation": f"{answer_result.processing_time:.2f}s"
                }
            }
            
            print(f"\n{'='*80}")
            print(f"[MULTI-AGENT] Total Processing Time: {total_time:.2f}s")
            print(f"[MULTI-AGENT] Breakdown:")
            for agent, timing in metadata["agent_timings"].items():
                agent_time = float(timing.replace('s', ''))
                percentage = (agent_time / total_time) * 100
                print(f"  - {agent}: {timing} ({percentage:.1f}%)")
            print(f"{'='*80}\n")
            
            return {
                "success": True,
                "answer": answer,
                "processing_time": f"{total_time:.2f}s",
                "question": question,
                "metadata": metadata
            }
            
        except Exception as e:
            print(f"[MULTI-AGENT] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
