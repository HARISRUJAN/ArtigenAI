import json
from typing import Optional
from sqlalchemy.orm import Session
from app.models.database import Document, Chunk
from app.services.rag_service import rag_service
from app.models.schemas import DocumentIngest

class IngestionService:
    def ingest_document(
        self,
        db: Session,
        document_data: DocumentIngest,
        origin_id: Optional[int] = None
    ) -> Document:
        """Ingest a document: chunk it, embed it, and store in DB"""
        # Create document record
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
        
        # Chunk the document
        chunks = rag_service.chunk_document(document_data.content)
        
        # Store chunks in vector DB and get point IDs
        chunk_ids = rag_service.store_document_chunks(
            document_id=db_document.id,
            title=document_data.title,
            source=document_data.source,
            url=document_data.url,
            chunks=chunks,
            chunk_metadata=[document_data.metadata] * len(chunks) if document_data.metadata else None
        )
        
        # Store chunk records in DB
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
        return db_document


ingestion_service = IngestionService()

