"""
RAG (Retrieval-Augmented Generation) Service

This service implements a RAG pipeline for AI governance document querying using:
1. Document chunking using spaCy semantic chunking (1 paragraph = 1 chunk)
2. Entity extraction using spaCy NER (stored in Qdrant payload)
3. Embedding generation using Nomic embeddings (sentence-transformers)
4. Vector storage and retrieval using Qdrant (semantic collection)
5. Answer generation using Groq LLM (primary) with OpenAI as fallback option

Architecture Decisions:
- Semantic chunking using spaCy (paragraph-based) for better context preservation
- Nomic embeddings (nomic-ai/nomic-embed-text-v1) are used for semantic search
  - 768-dimensional embeddings (local model, no API key needed)
  - Provides high-quality semantic representations for regulatory documents
- Groq is used for answer generation due to cost-effectiveness and performance
- OpenAI is kept as optional fallback for answer generation only
"""

import json
import uuid
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from groq import Groq

from app.services.vector_service import vector_service
from app.services.semantic_chunking_service import semantic_chunking_service
from app.core.config import settings


class RAGService:
    """
    Retrieval-Augmented Generation service for querying AI governance documents.
    
    This service combines:
    - Semantic chunking using spaCy (1 paragraph = 1 chunk)
    - Entity extraction using spaCy NER
    - Nomic embeddings for semantic search (768 dimensions)
    - Qdrant vector database for storage and retrieval (semantic collection)
    - Groq LLM for answer generation
    
    The RAG pipeline follows this flow:
    1. Documents are chunked using spaCy semantic chunking (paragraph-based)
    2. Entities are extracted from each chunk using spaCy NER
    3. Chunks are embedded using Nomic SentenceTransformer model
    4. Embeddings and entities are stored in Qdrant semantic collection
    5. Queries are embedded and used to retrieve relevant chunks
    6. Retrieved chunks with entities are used as context for LLM answer generation
    """
    
    def __init__(self):
        """
        Initialize RAG service with embeddings and LLM clients.
        
        Embeddings: Nomic SentenceTransformer (nomic-ai/nomic-embed-text-v1)
        - Local model, no API key required
        - 768-dimensional embeddings
        - trust_remote_code=True is required for this model
        
        Chunking: spaCy semantic chunking service
        - Paragraph-based chunking (1 paragraph = 1 chunk)
        - Entity extraction using spaCy NER
        
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
        
        # Semantic chunking service (initialized globally)
        self.semantic_chunker = semantic_chunking_service
    
    def chunk_document(self, content: str) -> List[Dict]:
        """
        Split a document into semantic chunks using spaCy (1 paragraph = 1 chunk).
        
        Uses spaCy semantic chunking to split text by paragraphs with entity extraction.
        Each chunk includes the content and extracted entities.
        
        Args:
            content: Full document text to chunk
            
        Returns:
            List of chunk dictionaries with:
            - content: Chunk text
            - entities: List of extracted entities (top N most frequent)
        """
        chunks = self.semantic_chunker.chunk_by_paragraphs(content)
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
        chunks: List[Dict],
        chunk_metadata: Optional[List[dict]] = None
    ) -> List[str]:
        """
        Store document chunks in the semantic vector database with embeddings and entities.
        
        This method implements the storage phase of the RAG pipeline:
        1. Extract chunk content and entities from semantic chunks
        2. Generate Nomic embeddings for all chunks
        3. Create Qdrant point IDs (UUIDs)
        4. Store embeddings, entities, and metadata in Qdrant semantic collection
        
        Args:
            document_id: Database ID of the document
            title: Document title for metadata
            source: Document source (e.g., "NIST", "EU")
            url: Optional document URL
            chunks: List of chunk dictionaries with 'content' and 'entities' keys
            chunk_metadata: Optional metadata for each chunk
            
        Returns:
            List of Qdrant point IDs for the stored chunks
        """
        # Extract chunk contents for embedding generation
        chunk_contents = [chunk["content"] for chunk in chunks]
        
        # Generate embeddings for all chunks using Nomic model
        embeddings = self.get_embeddings(chunk_contents)
        
        point_ids = []
        points_payloads = []
        
        # Prepare points for Qdrant storage
        # Qdrant requires point IDs to be either unsigned integers or UUIDs
        # We use UUIDs to ensure uniqueness across documents
        for idx, (chunk_dict, embedding) in enumerate(zip(chunks, embeddings)):
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
                "content": chunk_dict["content"],
                "entities": chunk_dict.get("entities", [])  # Include extracted entities
            }
            
            # Add optional chunk-level metadata if provided
            if chunk_metadata and idx < len(chunk_metadata):
                payload["metadata"] = json.dumps(chunk_metadata[idx])
            
            points_payloads.append(payload)
        
        # Store all embeddings in Qdrant semantic collection
        vector_service.add_embeddings(
            embeddings, 
            point_ids, 
            points_payloads,
            collection_name=settings.qdrant_semantic_collection_name
        )
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
        
        # Search Qdrant semantic collection for similar chunks using cosine similarity
        results = vector_service.search(
            query_embedding, 
            top_k=top_k,
            collection_name=settings.qdrant_semantic_collection_name
        )
        
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
                "entities": payload.get("entities", []),  # Include extracted entities
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
        # Format context chunks with source attribution and similarity scores
        # This provides the LLM with clear source information for citations
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            source_info = f"[Source {i}: {chunk['document_title']} ({chunk['document_source']})"
            if chunk.get('document_url'):
                source_info += f" - {chunk['document_url']}"
            source_info += "]"
            
            # Include entities if available for better context
            entities_info = ""
            if chunk.get('entities'):
                entities = chunk.get('entities', [])
                if isinstance(entities, list) and len(entities) > 0:
                    entity_names = [e.get('text', '') if isinstance(e, dict) else str(e) for e in entities[:5]]
                    entities_info = f"\n[Key entities: {', '.join(entity_names)}]"
            
            context_parts.append(f"{source_info}{entities_info}\n{chunk['content']}")
        
        context_text = "\n\n---\n\n".join(context_parts)
        
        # Construct improved RAG prompt with context and question
        # The prompt instructs the LLM to:
        # - Answer based on provided context
        # - Cite sources when relevant
        # - Indicate if context is insufficient
        # - Use structured, clear formatting
        prompt = f"""You are an expert AI governance assistant specializing in regulatory frameworks, standards, and best practices for AI governance, risk management, and compliance.

Your task is to answer the user's question using ONLY the provided context from authoritative sources. Follow these guidelines:

1. **Answer Accuracy**: Base your answer strictly on the provided context. Do not use external knowledge beyond what's in the context.

2. **Source Citation**: When referencing information, cite the specific source using the format: "According to [Source Name]..." or "As stated in [Source Name]..."

3. **Completeness**: Provide a comprehensive answer that addresses all aspects of the question if the context contains relevant information.

4. **Clarity**: Structure your answer clearly with:
   - A direct answer to the question
   - Supporting details and explanations
   - Specific examples or quotes from the context when relevant
   - Source citations
4.1 **Guidelines**:
- Provide accurate, cited information
- Acknowledge uncertainty when appropriate
- Focus on practical, actionable insights
- Maintain political neutrality
- Update: Current date is {current_date}

5. **Limitations**: If the context doesn't contain enough information to fully answer the question, clearly state what information is available and what is missing.

Context from documents:
{context_text}

Question: {question}

Provide your answer:"""

        # Generate answer using Groq LLM (primary)
        try:
            if not self.groq_client:
                raise ValueError("Groq API key not configured")
            
            completion = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert AI governance assistant. You provide accurate, well-sourced answers based on regulatory documents and frameworks. Always cite your sources and be precise in your responses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # Lower temperature for more focused, consistent answers
                max_completion_tokens=4096,  # Reasonable limit for detailed answers
                top_p=0.9,  # Slightly lower for more focused responses
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
