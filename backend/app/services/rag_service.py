"""
RAG (Retrieval-Augmented Generation) Service

This service implements a RAG pipeline for AI governance document querying using:
1. Document chunking using LangChain RecursiveCharacterTextSplitter
2. Embedding generation using Nomic embeddings (sentence-transformers)
3. Vector storage and retrieval using Qdrant
4. Answer generation using Groq LLM (primary) with OpenAI as fallback option

Architecture Decisions:
- Nomic embeddings (nomic-ai/nomic-embed-text-v1) are used for semantic search
  - 768-dimensional embeddings (local model, no API key needed)
  - Provides high-quality semantic representations for regulatory documents
- Groq is used for answer generation due to cost-effectiveness and performance
- LangChain components are integrated for document processing and RAG chain formation
- OpenAI is kept as optional fallback for answer generation only
"""

import json
import uuid
from typing import List, Dict, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from groq import Groq

from app.services.vector_service import vector_service
from app.core.config import settings


class RAGService:
    """
    Retrieval-Augmented Generation service for querying AI governance documents.
    
    This service combines:
    - Document chunking (1000 tokens, 200 overlap) using LangChain
    - Nomic embeddings for semantic search (768 dimensions)
    - Qdrant vector database for storage and retrieval
    - Groq LLM for answer generation
    
    The RAG pipeline follows this flow:
    1. Documents are chunked using LangChain's RecursiveCharacterTextSplitter
    2. Chunks are embedded using Nomic SentenceTransformer model
    3. Embeddings are stored in Qdrant vector database
    4. Queries are embedded and used to retrieve relevant chunks
    5. Retrieved chunks are used as context for LLM answer generation
    """
    
    def __init__(self):
        """
        Initialize RAG service with embeddings and LLM clients.
        
        Embeddings: Nomic SentenceTransformer (nomic-ai/nomic-embed-text-v1)
        - Local model, no API key required
        - 768-dimensional embeddings
        - trust_remote_code=True is required for this model
        
        LLM: Groq (primary) for answer generation
        - Uses openai/gpt-oss-20b model
        - OpenAI kept as optional fallback
        """
        # Initialize Nomic embedding model
        # This is a local model that runs on the machine - no API calls needed
        print("Loading Nomic embedding model (nomic-ai/nomic-embed-text-v1)...")
        self.embedding_model = SentenceTransformer(
            "nomic-ai/nomic-embed-text-v1",
            trust_remote_code=True  # Required for this model
        )
        print("[OK] Nomic embedding model loaded successfully")
        
        # Groq client for answer generation (primary LLM)
        self.groq_client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None
        
        # OpenAI client kept as optional fallback (commented out in generate_answer method)
        # Uncomment if you need to switch back to OpenAI:
        # from openai import OpenAI
        # self.openai_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        
        # LangChain text splitter configuration
        # 1000 token chunks with 200 token overlap ensures:
        # - Context preservation across chunk boundaries
        # - Manageable chunk sizes for embedding and retrieval
        # - Good balance between granularity and context
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def chunk_document(self, content: str) -> List[str]:
        """
        Split a document into overlapping chunks using LangChain.
        
        Uses RecursiveCharacterTextSplitter to intelligently split text while
        preserving context across chunk boundaries.
        
        Args:
            content: Full document text to chunk
            
        Returns:
            List of text chunks, each approximately 1000 tokens with 200 token overlap
        """
        chunks = self.text_splitter.split_text(content)
        return chunks
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using Nomic SentenceTransformer.
        
        This method uses the Nomic embedding model to convert text into
        768-dimensional vectors suitable for semantic search in Qdrant.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (each is 768-dimensional)
            
        Note:
            Nomic embeddings are generated locally - no API calls are made.
            The model.encode() method handles batching automatically for efficiency.
        """
        # Nomic model.encode() returns numpy array, convert to list of lists
        embeddings = self.embedding_model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        # Convert numpy array to list of lists for JSON serialization
        return embeddings.tolist()
    
    def store_document_chunks(
        self,
        document_id: int,
        title: str,
        source: str,
        url: Optional[str],
        chunks: List[str],
        chunk_metadata: Optional[List[dict]] = None
    ) -> List[str]:
        """
        Store document chunks in the vector database with embeddings.
        
        This method implements the storage phase of the RAG pipeline:
        1. Generate Nomic embeddings for all chunks
        2. Create Qdrant point IDs (format: {document_id}_{chunk_index})
        3. Store embeddings and metadata in Qdrant vector database
        
        Args:
            document_id: Database ID of the document
            title: Document title for metadata
            source: Document source (e.g., "NIST", "EU")
            url: Optional document URL
            chunks: List of text chunks to store
            chunk_metadata: Optional metadata for each chunk
            
        Returns:
            List of Qdrant point IDs for the stored chunks
        """
        # Generate embeddings for all chunks using Nomic model
        embeddings = self.get_embeddings(chunks)
        
        point_ids = []
        points_payloads = []
        
        # Prepare points for Qdrant storage
        # Qdrant requires point IDs to be either unsigned integers or UUIDs
        # We use UUIDs to ensure uniqueness across documents
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())  # Generate UUID for each chunk
            point_ids.append(point_id)
            
            # Metadata payload for retrieval context
            # This metadata is used during retrieval to provide source attribution
            payload = {
                "document_id": document_id,
                "title": title,
                "source": source,
                "url": url,
                "chunk_index": idx,
                "content": chunk
            }
            
            # Add optional chunk-level metadata if provided
            if chunk_metadata and idx < len(chunk_metadata):
                payload["metadata"] = json.dumps(chunk_metadata[idx])
            
            points_payloads.append(payload)
        
        # Store all embeddings in Qdrant vector database
        vector_service.add_embeddings(embeddings, point_ids, points_payloads)
        return point_ids
    
    def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Retrieve the most relevant document chunks for a query using semantic search.
        
        This method implements the retrieval phase of the RAG pipeline:
        1. Generate Nomic embedding for the query
        2. Search Qdrant for top-k similar chunks using cosine similarity
        3. Return chunks with metadata and similarity scores
        
        Args:
            query: User's question or search query
            top_k: Number of top results to return (default: 5)
            
        Returns:
            List of chunk dictionaries with:
            - content: The chunk text
            - document_title: Source document title
            - document_source: Source organization
            - document_url: Source document URL
            - chunk_index: Index of chunk in document
            - score: Cosine similarity score (0-1, higher is more similar)
            - metadata: Additional chunk metadata
        """
        # Generate query embedding using Nomic model
        # Single query embedding for semantic search
        query_embedding = self.embedding_model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()
        
        # Search Qdrant for similar chunks using cosine similarity
        results = vector_service.search(query_embedding, top_k=top_k)
        
        # Format results with metadata for answer generation
        chunks = []
        for result in results:
            payload = result["payload"]
            chunks.append({
                "content": payload.get("content", ""),
                "document_title": payload.get("title", ""),
                "document_source": payload.get("source", ""),
                "document_url": payload.get("url"),
                "chunk_index": payload.get("chunk_index", 0),
                "score": result["score"],  # Cosine similarity score (0-1)
                "metadata": json.loads(payload.get("metadata", "{}")) if payload.get("metadata") else {}
            })
        
        return chunks
    
    def generate_answer(
        self,
        question: str,
        context_chunks: List[Dict]
    ) -> str:
        """
        Generate an answer to a question using retrieved context chunks.
        
        This method implements the generation phase of the RAG pipeline:
        1. Format retrieved chunks with source attribution
        2. Construct prompt with context and question
        3. Generate answer using Groq LLM (primary) or OpenAI (fallback)
        
        The RAG chain flow:
        - Retrieval: Relevant chunks retrieved via semantic search
        - Augmentation: Chunks formatted with metadata as context
        - Generation: LLM generates answer based on context and question
        
        Args:
            question: User's question
            context_chunks: Retrieved relevant document chunks with metadata
            
        Returns:
            Generated answer string with citations
            
        Note:
            Uses Groq (openai/gpt-oss-20b) as primary LLM.
            OpenAI code is commented below as fallback option.
        """
        # Format context chunks with source attribution
        # This provides the LLM with clear source information for citations
        context_text = "\n\n".join([
            f"[Source: {chunk['document_title']} ({chunk['document_source']})]\n{chunk['content']}"
            for chunk in context_chunks
        ])
        
        # Construct RAG prompt with context and question
        # The prompt instructs the LLM to:
        # - Answer based on provided context
        # - Cite sources when relevant
        # - Indicate if context is insufficient
        prompt = f"""You are an AI governance expert assistant. Answer the following question based on the provided context from regulatory documents and frameworks.

Context:
{context_text}

Question: {question}

Provide a clear, accurate answer based on the context. If the context doesn't contain enough information to answer the question, say so. Cite the sources in your answer when relevant."""

        # Generate answer using Groq LLM (primary)
        try:
            if not self.groq_client:
                raise ValueError("Groq API key not configured")
            
            completion = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI governance literacy assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=1,
                max_completion_tokens=8192,
                top_p=1,
                reasoning_effort="medium",
                stream=False  # Non-streaming for simplicity
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            # Fallback error message if Groq fails
            error_msg = f"Error generating answer: {str(e)}"
            
            # Alternative: Uncomment below to use OpenAI as fallback
            # if self.openai_client:
            #     try:
            #         response = self.openai_client.chat.completions.create(
            #             model="gpt-4",
            #             messages=[
            #                 {"role": "system", "content": "You are a helpful AI governance literacy assistant."},
            #                 {"role": "user", "content": prompt}
            #             ],
            #             temperature=0.7,
            #             max_tokens=1000
            #         )
            #         return response.choices[0].message.content
            #     except Exception as fallback_error:
            #         return f"Error: Unable to generate answer. {error_msg} Fallback also failed: {str(fallback_error)}"
            
            return f"Error: Unable to generate answer. {error_msg} Please check your Groq API key configuration."


# Global RAG service instance
# This singleton pattern ensures the embedding model is loaded once and reused
rag_service = RAGService()
