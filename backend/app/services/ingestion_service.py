import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.database import Document, Chunk
from app.services.rag_service import rag_service
from app.models.schemas import DocumentIngest

logger = logging.getLogger(__name__)

class IngestionService:
    def ingest_document(
        self,
        db: Session,
        document_data: DocumentIngest,
        origin_id: Optional[int] = None
    ) -> Document:
        """
        Ingest a document: chunk it, embed it, and store in Qdrant vector DB.
        
        Steps:
        1. Create document record in database
        2. Chunk the document content
        3. Generate embeddings and store in Qdrant
        4. Store chunk records in database
        """
        try:
            logger.info(f"Starting ingestion for document: {document_data.title} ({len(document_data.content)} chars)")
            
            # Step 1: Create document record
            logger.debug("Creating document record in database")
            db_document = Document(
                title=document_data.title,
                source=document_data.source,
                url=document_data.url,
                content=document_data.content,
                document_metadata=json.dumps(document_data.metadata) if document_data.metadata else None,
                origin_id=origin_id
            )
            db.add(db_document)
            db.flush()  # Get the ID
            logger.info(f"Created document record with ID: {db_document.id}")
            
            # Step 2: Chunk the document
            logger.debug("Chunking document content")
            chunks = rag_service.chunk_document(document_data.content)
            logger.info(f"Document chunked into {len(chunks)} chunks")
            
            if not chunks:
                raise ValueError("Document chunking resulted in zero chunks")
            
            # Step 3: Store chunks in vector DB and get point IDs
            logger.debug("Generating embeddings and storing in Qdrant")
            try:
                chunk_ids = rag_service.store_document_chunks(
                    document_id=db_document.id,
                    title=document_data.title,
                    source=document_data.source,
                    url=document_data.url,
                    chunks=chunks,
                    chunk_metadata=[document_data.metadata] * len(chunks) if document_data.metadata else None
                )
                logger.info(f"Stored {len(chunk_ids)} chunks in Qdrant vector database")
                
                if len(chunk_ids) != len(chunks):
                    logger.warning(f"Mismatch: {len(chunks)} chunks but {len(chunk_ids)} point IDs returned")
            except Exception as qdrant_error:
                # Qdrant-specific error - log and re-raise with clear message
                error_msg = f"Qdrant ingestion failed: {str(qdrant_error)}"
                logger.exception(f"Qdrant error during ingestion for document {db_document.id}: {error_msg}")
                # Re-raise with Qdrant prefix so caller can distinguish it
                raise Exception(f"QDRANT_ERROR: {error_msg}") from qdrant_error
            
            # Step 4: Store chunk records in DB
            logger.debug("Storing chunk records in database")
            for idx, (chunk_content, point_id) in enumerate(zip(chunks, chunk_ids)):
                db_chunk = Chunk(
                    document_id=db_document.id,
                    content=chunk_content,
                    chunk_index=idx,
                    embedding_id=point_id,
                    chunk_metadata=json.dumps(document_data.metadata) if document_data.metadata else None
                )
                db.add(db_chunk)
            
            db.commit()
            db.refresh(db_document)
            logger.info(f"✓ Successfully ingested document ID: {db_document.id} with {len(chunks)} chunks")
            
            return db_document
            
        except Exception as e:
            logger.exception(f"Error during document ingestion: {str(e)}")
            db.rollback()
            raise


ingestion_service = IngestionService()

