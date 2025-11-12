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
    try:
        # Retrieve relevant chunks
        chunks = rag_service.retrieve_relevant_chunks(query.question, top_k=query.top_k)
        
        if not chunks:
            return RAGResponse(
                answer="I couldn't find relevant information to answer your question. Please try rephrasing or ask about a different topic.",
                citations=[]
            )
        
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
                metadata=chunk.get("metadata")
            )
            for chunk in chunks
        ]
        
        return RAGResponse(answer=answer, citations=citations)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )

