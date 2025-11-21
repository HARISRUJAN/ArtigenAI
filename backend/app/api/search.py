from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.schemas import RAGQuery, RAGResponse, DocumentChunk
from app.services.rag_service import rag_service
from app.utils.string_utils import escape_for_fstring

router = APIRouter()


@router.post("/query", response_model=RAGResponse)
async def query_rag(
    query: RAGQuery,
    db: Session = Depends(get_db)
):
    """Query the RAG system with a question"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Escape question to prevent f-string evaluation errors
        question_safe = escape_for_fstring(query.question[:100] if len(query.question) > 100 else query.question)
        logger.info(f"Processing RAG query: {question_safe}...")
        
        # Retrieve relevant chunks with error handling
        try:
            chunks = rag_service.retrieve_relevant_chunks(query.question, top_k=query.top_k)
        except Exception as chunk_error:
            logger.error(f"Error retrieving chunks: {chunk_error}")
            # Check if it's a Qdrant connection error
            error_msg = str(chunk_error).lower()
            if "qdrant" in error_msg or "connection" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Vector database is currently unavailable. Please try again later."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error retrieving information: {str(chunk_error)}"
                )
        
        # Check if web fallback is needed
        from app.core.config import settings
        from app.services.realtime_web_service import requires_freshness, realtime_web_service
        
        enable_realtime_web = getattr(settings, 'enable_realtime_web', False)
        min_similarity_threshold = getattr(settings, 'min_similarity_threshold', 0.6)
        min_results = getattr(settings, 'min_results', 3)
        
        web_chunks = []
        should_use_web = False
        
        if enable_realtime_web and query.use_web_fallback:
            # Check if web fallback should be triggered
            top_score = chunks[0].get("score", 0.0) if chunks else 0.0
            needs_freshness = requires_freshness(query.question)
            
            if (not chunks or len(chunks) < min_results or 
                top_score < min_similarity_threshold or needs_freshness):
                should_use_web = True
                logger.info(f"Triggering web fallback for query: {question_safe[:100]}... (chunks={len(chunks)}, score={top_score:.2f}, freshness={needs_freshness})")
        
        # Fetch fresh web content if needed
        if should_use_web:
            try:
                web_max_pages = getattr(settings, 'realtime_web_max_pages', 10)
                web_max_seconds = getattr(settings, 'realtime_web_max_seconds', 5.0)
                
                web_results = await realtime_web_service.fetch_fresh_content(
                    query=query.question,
                    max_pages=web_max_pages,
                    max_depth=1,
                    max_seconds=web_max_seconds
                )
                
                # Convert web crawl results to chunk format for RAG
                for result in web_results:
                    markdown = result.get("markdown", "")
                    if markdown:
                        # Create a chunk-like dict from web result
                        web_chunks.append({
                            "content": markdown[:2000],  # Limit length
                            "document_title": result.get("metadata", {}).get("title", "Web Result"),
                            "document_source": "Web (Live)",
                            "document_url": result.get("url"),
                            "chunk_index": 0,
                            "score": 0.7,  # Default score for web results
                            "metadata": {
                                "source_type": "web_live",
                                "fetched_at": result.get("metadata", {}).get("fetched_at")
                            }
                        })
                
                logger.info(f"Fetched {len(web_chunks)} web chunks for query")
                
            except Exception as web_error:
                logger.warning(f"Web fallback failed: {web_error}, continuing with local results only")
        
        # Merge local and web chunks (local first, web supplements)
        all_chunks = chunks + web_chunks
        
        if not all_chunks:
            logger.warning(f"No relevant chunks found for query: {question_safe}...")
            return RAGResponse(
                answer="I couldn't find relevant information to answer your question. This could mean:\n1. No documents have been ingested yet - please ingest some documents first.\n2. The question doesn't match any content in the knowledge base - try rephrasing or asking about a different topic.",
                citations=[]
            )
        
        logger.info(f"Retrieved {len(chunks)} local chunks, {len(web_chunks)} web chunks, generating answer...")
        
        # Initialize answer variable
        answer = None
        
        # Generate answer with error handling (use all chunks: local + web)
        try:
            answer = rag_service.generate_answer(query.question, all_chunks)
            
            # Additional safety check: ensure answer doesn't contain code errors
            if answer and ("current_date" in answer.lower() or "is not defined" in answer.lower()):
                answer_safe = escape_for_fstring(answer[:200])
                logger.warning(f"Answer contains code-like content, attempting to clean: {answer_safe}...")
                # Remove any lines containing code-like patterns
                lines = answer.split('\n')
                cleaned = []
                for line in lines:
                    if not any(pattern in line.lower() for pattern in ["current_date", "is not defined", "nameerror", "def ", "import ", "datetime"]):
                        cleaned.append(line)
                answer = '\n'.join(cleaned).strip()
                if not answer:
                    answer = "I apologize, but I encountered an issue generating a proper response. Please try rephrasing your question."
        except ValueError as ve:
            # Handle value errors from LLM response generation (including API errors)
            logger.error(f"ValueError during answer generation: {ve}")
            error_msg = str(ve)
            # Check if it's an API configuration error
            if "api key" in error_msg.lower() or "groq" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI service is currently unavailable. Please check the API configuration."
                )
            # Check if it's a code generation error
            elif "code errors" in error_msg.lower() or "invalid response" in error_msg.lower():
                answer = "I apologize, but I encountered an issue generating a proper response. The system attempted to generate code instead of a text answer. Please try rephrasing your question."
            else:
                # Re-raise other ValueErrors to be caught by outer exception handler
                raise
        
        # Ensure answer is set before formatting citations
        if not answer or not answer.strip():
            logger.warning("Answer is empty or None, using fallback message")
            answer = "I apologize, but I encountered an issue generating a proper response. Please try again or rephrasing your question."
        
        # Format citations with error handling (include both local and web chunks)
        citations = []
        try:
            for chunk in all_chunks:
                try:
                    citations.append(DocumentChunk(
                        content=chunk.get("content", ""),
                        document_title=chunk.get("document_title", ""),
                        document_source=chunk.get("document_source", ""),
                        document_url=chunk.get("document_url"),
                        chunk_index=chunk.get("chunk_index", 0),
                        entities=chunk.get("entities", []),  # Include extracted entities
                        metadata=chunk.get("metadata", {})
                    ))
                except Exception as citation_error:
                    logger.warning(f"Error formatting citation: {citation_error}, skipping chunk")
                    continue
        except Exception as citations_error:
            logger.error(f"Error formatting citations: {citations_error}")
            citations = []  # Return empty citations if formatting fails
        
        logger.info(f"Successfully generated answer for query (answer length: {len(answer)}, citations: {len(citations)})")
        return RAGResponse(answer=answer, citations=citations)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 503 Service Unavailable) as-is
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.exception(f"Error processing RAG query: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )

