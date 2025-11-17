from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.schemas import RAGQuery, RAGResponse, DocumentChunk
from app.services.rag_service import rag_service

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
        logger.info(f"Processing RAG query: {query.question[:100]}...")
        
        # Retrieve relevant chunks
        chunks = rag_service.retrieve_relevant_chunks(query.question, top_k=query.top_k)
        
        if not chunks:
            logger.warning(f"No relevant chunks found for query: {query.question[:100]}...")
            return RAGResponse(
                answer="I couldn't find relevant information to answer your question. This could mean:\n1. No documents have been ingested yet - please ingest some documents first.\n2. The question doesn't match any content in the knowledge base - try rephrasing or asking about a different topic.",
                citations=[]
            )
        
        logger.info(f"Retrieved {len(chunks)} relevant chunks, generating answer...")
        
        # Generate answer
        answer = rag_service.generate_answer(query.question, chunks)
        
        # Format citations
        citations = [
            DocumentChunk(
                content=chunk["content"],
                document_title=chunk["document_title"],
                document_source=chunk["document_source"],
                document_url=chunk.get("document_url"),
                chunk_index=chunk["chunk_index"],
                entities=chunk.get("entities", []),  # Include extracted entities
                metadata=chunk.get("metadata")
            )
            for chunk in chunks
        ]
        
        logger.info(f"Successfully generated answer for query")
        return RAGResponse(answer=answer, citations=citations)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.exception(f"Error processing RAG query: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )

