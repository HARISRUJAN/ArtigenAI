from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings

class VectorService:
    def __init__(self):
        self.client = None
        self.collection_name = settings.qdrant_collection_name
        self._initialized = False
    
    def _init_client(self):
        """Lazy initialization of Qdrant client"""
        if not self._initialized:
            import logging
            logger = logging.getLogger(__name__)
            try:
                # Support both local and cloud Qdrant
                if settings.qdrant_api_key:
                    # Qdrant Cloud with API key
                    logger.debug(f"Initializing Qdrant client with API key at {settings.qdrant_url}")
                    self.client = QdrantClient(
                        url=settings.qdrant_url,
                        api_key=settings.qdrant_api_key
                    )
                else:
                    # Local Qdrant or cloud without API key
                    logger.debug(f"Initializing Qdrant client without API key at {settings.qdrant_url}")
                    self.client = QdrantClient(url=settings.qdrant_url)
                
                # Test connection by getting collections
                try:
                    self.client.get_collections()
                    logger.info(f"Successfully connected to Qdrant at {settings.qdrant_url}")
                except Exception as conn_error:
                    error_type = type(conn_error).__name__
                    error_str = str(conn_error) if str(conn_error) else repr(conn_error)
                    logger.error(f"Failed to connect to Qdrant at {settings.qdrant_url} ({error_type}): {error_str}")
                    
                    # Provide specific error messages
                    if "authentication" in error_str.lower() or "unauthorized" in error_str.lower():
                        raise Exception(f"Qdrant authentication failed ({error_type}: {error_str}). Please check your Qdrant API key.") from conn_error
                    elif "connection" in error_str.lower() or "timeout" in error_str.lower():
                        raise Exception(f"Qdrant connection failed ({error_type}: {error_str}). Please check if Qdrant is accessible at {settings.qdrant_url}") from conn_error
                    else:
                        raise Exception(f"Qdrant connection test failed ({error_type}: {error_str})") from conn_error
                
                self._ensure_collection()
                self._initialized = True
            except Exception as init_error:
                logger.exception(f"Error initializing Qdrant client: {str(init_error)}")
                raise
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.client:
            self._init_client()
        
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection '{self.collection_name}' with 768-dimensional vectors")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=768,  # Nomic embed-text-v1 embedding size (768 dimensions)
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Successfully created Qdrant collection '{self.collection_name}'")
            else:
                # Verify collection configuration matches our requirements
                collection_info = self.client.get_collection(self.collection_name)
                logger.debug(f"Qdrant collection '{self.collection_name}' already exists")
                logger.debug(f"Collection config: vectors={collection_info.config.params.vectors.size}, distance={collection_info.config.params.vectors.distance}")
                
                # Verify vector size matches (768 for Nomic)
                if hasattr(collection_info.config.params.vectors, 'size'):
                    vector_size = collection_info.config.params.vectors.size
                    if vector_size != 768:
                        logger.warning(f"Collection vector size mismatch: expected 768, got {vector_size}. This may cause issues.")
        except Exception as e:
            error_type = type(e).__name__
            error_str = str(e) if str(e) else repr(e)
            logger.exception(f"Error ensuring Qdrant collection exists ({error_type}): {error_str}")
            raise Exception(f"Failed to ensure Qdrant collection '{self.collection_name}': {error_str}") from e
    
    def add_embeddings(
        self,
        embeddings: List[List[float]],
        ids: List[str],
        payloads: List[dict]
    ):
        """
        Add embeddings to Qdrant vector database.
        
        Args:
            embeddings: List of embedding vectors (each is 768-dimensional for Nomic)
            ids: List of point IDs (UUIDs as strings)
            payloads: List of metadata dictionaries for each point
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not self._initialized:
            self._init_client()
        
        if not embeddings or not ids or not payloads:
            logger.warning("Empty embeddings, ids, or payloads provided to add_embeddings")
            return
        
        if len(embeddings) != len(ids) or len(ids) != len(payloads):
            raise ValueError(f"Mismatch in lengths: embeddings={len(embeddings)}, ids={len(ids)}, payloads={len(payloads)}")
        
        logger.debug(f"Preparing {len(embeddings)} points for Qdrant upsert")
        
        points = [
            PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            for point_id, embedding, payload in zip(ids, embeddings, payloads)
        ]
        
        try:
            logger.debug(f"Connecting to Qdrant at {settings.qdrant_url}")
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Successfully upserted {len(points)} points to Qdrant collection '{self.collection_name}'")
        except Exception as e:
            error_type = type(e).__name__
            error_details = str(e) if str(e) else repr(e)
            logger.exception(f"Qdrant upsert error ({error_type}): {error_details}")
            
            # Provide more specific error messages based on error type
            if "Connection" in error_type or "connect" in error_details.lower() or "timeout" in error_details.lower():
                raise Exception(f"Qdrant connection failed ({error_type}: {error_details}). Please check if Qdrant is accessible at {settings.qdrant_url}") from e
            elif "collection" in error_details.lower() and "not found" in error_details.lower():
                raise Exception(f"Qdrant collection '{self.collection_name}' not found ({error_type}: {error_details}). Please ensure the collection exists.") from e
            elif "authentication" in error_details.lower() or "unauthorized" in error_details.lower() or "forbidden" in error_details.lower():
                raise Exception(f"Qdrant authentication failed ({error_type}: {error_details}). Please check your Qdrant API key and permissions.") from e
            elif "rate limit" in error_details.lower() or "quota" in error_details.lower():
                raise Exception(f"Qdrant rate limit or quota exceeded ({error_type}: {error_details}). Please check your Qdrant Cloud plan limits.") from e
            else:
                raise Exception(f"Qdrant operation failed ({error_type}: {error_details})") from e
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_conditions: Optional[dict] = None
    ) -> List[dict]:
        """Search for similar embeddings"""
        if not self._initialized:
            self._init_client()
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=filter_conditions
        )
        
        results = []
        for result in search_result:
            results.append({
                "id": result.id,
                "score": result.score,
                "payload": result.payload
            })
        
        return results
    
    def delete_points(self, point_ids: List[str]):
        """Delete points by IDs"""
        if not self._initialized:
            self._init_client()
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=point_ids
        )


# Lazy initialization - will connect when first used
vector_service = VectorService()

